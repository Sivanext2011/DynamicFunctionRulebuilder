"""Package Builder: Produces CHA-compatible import ZIP packages."""
from __future__ import annotations
import io
import time
import zipfile
from ..models import DynamicFunction
from ..serializer import XmlSerializer


class PackageBuilder:
    """Builds a CHA import package (ZIP) from a DynamicFunction object model.

    Uses the baseconfig/deployment package format (no checksums, no manifests):
        OuterZip/
        └── ChargingConfig.zip
            └── dynamicfunction/
                └── DynamicFunctions#<Name>#<Version>.xml
    """

    def __init__(self, config_version: str = "1.0.0"):
        self.config_version = config_version
        self._xml_serializer = XmlSerializer()

    def build(self, func: DynamicFunction, version: str | None = None) -> bytes:
        """Build a complete CHA import ZIP package."""
        if version is None:
            version = self.config_version

        xml_content = self._xml_serializer.serialize(func)
        xml_bytes = xml_content.encode('utf-8')
        xml_filename = f"DynamicFunctions#{func.name}#{version}.xml"

        # Build inner ChargingConfig.zip
        inner_buf = io.BytesIO()
        with zipfile.ZipFile(inner_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"dynamicfunction/{xml_filename}", xml_bytes)

        # Build outer zip
        outer_buf = io.BytesIO()
        with zipfile.ZipFile(outer_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("ChargingConfig.zip", inner_buf.getvalue())

        return outer_buf.getvalue()

    def build_multi(self, functions: list[tuple[DynamicFunction, str | None]]) -> bytes:
        """Build a package with multiple dynamic functions."""
        inner_buf = io.BytesIO()
        with zipfile.ZipFile(inner_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for func, version in functions:
                ver = version or self.config_version
                xml_content = self._xml_serializer.serialize(func)
                xml_filename = f"DynamicFunctions#{func.name}#{ver}.xml"
                zf.writestr(f"dynamicfunction/{xml_filename}", xml_content.encode('utf-8'))

        outer_buf = io.BytesIO()
        with zipfile.ZipFile(outer_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("ChargingConfig.zip", inner_buf.getvalue())

        return outer_buf.getvalue()
