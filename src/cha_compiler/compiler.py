"""CHA Configuration Compiler - Main entry point."""
from __future__ import annotations
import io
import os
import zipfile
from .models import DynamicFunction
from .parser import DSLParser, DSLParseError
from .parser.dsl_decompiler import DSLDecompiler
from .serializer import XmlSerializer, XmlParser
from .package_builder import PackageBuilder
from .validator import Validator, ValidationError


class CompileError(Exception):
    def __init__(self, errors: list[ValidationError]):
        self.errors = errors
        super().__init__("; ".join(e.message for e in errors))


class CHACompiler:
    """Main compiler facade."""

    def __init__(self, config_version: str = "1.0.0"):
        self._parser = DSLParser()
        self._decompiler = DSLDecompiler()
        self._xml_serializer = XmlSerializer()
        self._xml_parser = XmlParser()
        self._builder = PackageBuilder(config_version=config_version)
        self._validator = Validator()

    def compile(self, dsl_text: str, version: str | None = None) -> bytes:
        """Compile DSL text to a CHA import ZIP package."""
        func = self._parser.parse(dsl_text)
        errors = self._validator.validate(func)
        if errors:
            raise CompileError(errors)
        return self._builder.build(func, version=version)

    def compile_batch(self, dsl_files: list[str], version: str | None = None) -> bytes:
        """Compile multiple DSL files into a single CHA import package."""
        functions = []
        for path in dsl_files:
            dsl_text = open(path, 'r', encoding='utf-8').read()
            func = self._parser.parse(dsl_text)
            errors = self._validator.validate(func)
            if errors:
                raise CompileError(errors)
            functions.append((func, version))
        return self._builder.build_multi(functions)

    def decompile(self, zip_bytes: bytes) -> str:
        """Decompile a CHA export ZIP package back to DSL (first function found)."""
        func = self.load(zip_bytes)
        return self._decompiler.decompile(func)

    def load(self, zip_bytes: bytes) -> DynamicFunction:
        """Load a DynamicFunction from a CHA ZIP package (first XML found)."""
        xml_content = self._extract_xml_from_package(zip_bytes)
        return self._xml_parser.parse(xml_content)

    def load_all(self, zip_bytes: bytes) -> list[DynamicFunction]:
        """Load ALL DynamicFunctions from a CHA export package."""
        xml_contents = self._extract_all_xml_from_package(zip_bytes)
        functions = []
        for xml in xml_contents:
            try:
                functions.append(self._xml_parser.parse(xml))
            except Exception:
                pass  # Skip malformed XMLs
        return functions

    def export_inventory(self, zip_bytes: bytes, output_dir: str) -> list[str]:
        """Decompile all functions from a CHA export into individual .dsl files."""
        functions = self.load_all(zip_bytes)
        os.makedirs(output_dir, exist_ok=True)
        written = []
        for func in functions:
            dsl = self._decompiler.decompile(func)
            filename = f"{func.name}.dsl"
            path = os.path.join(output_dir, filename)
            # Avoid overwriting (multiple versions) - keep latest
            with open(path, 'w', encoding='utf-8') as f:
                f.write(dsl)
            if path not in written:
                written.append(path)
        return written

    def diff(self, zip_bytes_a: bytes, zip_bytes_b: bytes) -> dict:
        """Compare two CHA exports and return differences.

        Returns dict with keys: added, removed, modified (each is list of function names).
        modified entries include the DSL diff.
        """
        funcs_a = {f.name: f for f in self.load_all(zip_bytes_a)}
        funcs_b = {f.name: f for f in self.load_all(zip_bytes_b)}

        names_a = set(funcs_a.keys())
        names_b = set(funcs_b.keys())

        added = sorted(names_b - names_a)
        removed = sorted(names_a - names_b)
        modified = []

        for name in sorted(names_a & names_b):
            dsl_a = self._decompiler.decompile(funcs_a[name])
            dsl_b = self._decompiler.decompile(funcs_b[name])
            if dsl_a != dsl_b:
                modified.append({"name": name, "before": dsl_a, "after": dsl_b})

        return {"added": added, "removed": removed, "modified": modified}

    def to_dsl(self, func: DynamicFunction) -> str:
        return self._decompiler.decompile(func)

    def to_xml(self, func: DynamicFunction) -> str:
        return self._xml_serializer.serialize(func)

    def parse_dsl(self, dsl_text: str) -> DynamicFunction:
        return self._parser.parse(dsl_text)

    def validate(self, func: DynamicFunction) -> list[ValidationError]:
        return self._validator.validate(func)

    def format_dsl(self, dsl_text: str) -> str:
        """Auto-format DSL: normalize indentation, blank lines, parameter order."""
        func = self._parser.parse(dsl_text)
        return self._decompiler.decompile(func)

    def _extract_xml_from_package(self, zip_bytes: bytes) -> str:
        xmls = self._extract_all_xml_from_package(zip_bytes)
        if not xmls:
            raise ValueError("No XML file found in CHA package")
        return xmls[0]

    def _extract_all_xml_from_package(self, zip_bytes: bytes) -> list[str]:
        """Recursively extract all Dynamic Function XMLs from a package."""
        results = []
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            names = zf.namelist()
            inner_zips = [n for n in names if n.endswith('.zip')]
            xml_files = [n for n in names if n.endswith('.xml')]

            if inner_zips and not xml_files:
                # Recurse into inner zip(s)
                for iz_name in inner_zips:
                    inner_data = zf.read(iz_name)
                    results.extend(self._extract_all_xml_from_package(inner_data))
            else:
                # Collect XMLs at this level
                for xf in xml_files:
                    try:
                        results.append(zf.read(xf).decode('utf-8'))
                    except Exception:
                        pass
                # Also recurse into any nested zips
                for iz_name in inner_zips:
                    inner_data = zf.read(iz_name)
                    results.extend(self._extract_all_xml_from_package(inner_data))

        return results
