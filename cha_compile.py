"""CHA Configuration Compiler CLI."""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cha_compiler import CHACompiler, CompileError
from cha_compiler.parser.nl_advanced import AdvancedNLToDSL
from cha_compiler.parser.nl_parser import NLParseError
from cha_compiler.validator import Validator


def cmd_compile(args):
    compiler = CHACompiler()
    dsl_text = open(args.input, 'r', encoding='utf-8').read()
    try:
        zip_bytes = compiler.compile(dsl_text, version=args.version)
    except CompileError as e:
        print(f"Compilation failed:", file=sys.stderr)
        for err in e.errors:
            print(f"  [{err.severity}] {err.message}", file=sys.stderr)
        sys.exit(1)

    output = args.output or os.path.splitext(os.path.basename(args.input))[0] + ".zip"
    with open(output, 'wb') as f:
        f.write(zip_bytes)
    print(f"Generated: {output} ({len(zip_bytes)} bytes)")


def cmd_batch(args):
    """Compile all DSL files in a directory into a single CHA package."""
    compiler = CHACompiler()
    pattern = os.path.join(args.input, "*.dsl")
    dsl_files = sorted(glob.glob(pattern))
    if not dsl_files:
        print(f"No .dsl files found in {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"Compiling {len(dsl_files)} files...")
    try:
        zip_bytes = compiler.compile_batch(dsl_files, version=args.version)
    except CompileError as e:
        print(f"Compilation failed:", file=sys.stderr)
        for err in e.errors:
            print(f"  [{err.severity}] {err.message}", file=sys.stderr)
        sys.exit(1)

    output = args.output or "batch_output.zip"
    with open(output, 'wb') as f:
        f.write(zip_bytes)
    print(f"Generated: {output} ({len(zip_bytes)} bytes) with {len(dsl_files)} functions")
    for f in dsl_files:
        print(f"  - {os.path.basename(f)}")


def cmd_decompile(args):
    compiler = CHACompiler()
    zip_bytes = open(args.input, 'rb').read()
    dsl_text = compiler.decompile(zip_bytes)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(dsl_text)
        print(f"Decompiled to: {args.output}")
    else:
        print(dsl_text)


def cmd_export(args):
    """Export all functions from a CHA package into individual DSL files."""
    compiler = CHACompiler()
    zip_bytes = open(args.input, 'rb').read()
    output_dir = args.output or "exported_dsl"
    written = compiler.export_inventory(zip_bytes, output_dir)
    print(f"Exported {len(written)} functions to {output_dir}/")
    for path in sorted(written):
        print(f"  - {os.path.basename(path)}")


def cmd_diff(args):
    """Compare two CHA exports and show changes."""
    compiler = CHACompiler()
    zip_a = open(args.file_a, 'rb').read()
    zip_b = open(args.file_b, 'rb').read()
    result = compiler.diff(zip_a, zip_b)

    if result["added"]:
        print(f"\n+++ ADDED ({len(result['added'])}):")
        for name in result["added"]:
            print(f"  + {name}")

    if result["removed"]:
        print(f"\n--- REMOVED ({len(result['removed'])}):")
        for name in result["removed"]:
            print(f"  - {name}")

    if result["modified"]:
        print(f"\n~~~ MODIFIED ({len(result['modified'])}):")
        for item in result["modified"]:
            print(f"\n  ~ {item['name']}:")
            # Simple line diff
            before_lines = item["before"].splitlines()
            after_lines = item["after"].splitlines()
            for line in before_lines:
                if line not in after_lines:
                    print(f"    - {line}")
            for line in after_lines:
                if line not in before_lines:
                    print(f"    + {line}")

    if not any(result.values()):
        print("No differences found.")


def cmd_validate(args):
    compiler = CHACompiler()
    dsl_text = open(args.input, 'r', encoding='utf-8').read()
    func = compiler.parse_dsl(dsl_text)

    errors = compiler.validate(func)
    warnings = Validator().validate_warnings(func)

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  [{w.severity}] {w.message}")

    if errors:
        print("Errors:")
        for err in errors:
            print(f"  [{err.severity}] {err.message}")
        sys.exit(1)
    else:
        print("Valid.")


def cmd_format(args):
    """Auto-format a DSL file (normalize indentation and structure)."""
    compiler = CHACompiler()
    dsl_text = open(args.input, 'r', encoding='utf-8').read()
    formatted = compiler.format_dsl(dsl_text)
    if args.inplace:
        with open(args.input, 'w', encoding='utf-8') as f:
            f.write(formatted)
        print(f"Formatted: {args.input}")
    elif args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(formatted)
        print(f"Formatted to: {args.output}")
    else:
        print(formatted)


def cmd_xml(args):
    compiler = CHACompiler()
    dsl_text = open(args.input, 'r', encoding='utf-8').read()
    func = compiler.parse_dsl(dsl_text)
    xml_text = compiler.to_xml(func)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(xml_text)
        print(f"XML written to: {args.output}")
    else:
        print(xml_text)


def cmd_english(args):
    nl_text = open(args.input, 'r', encoding='utf-8').read()
    try:
        dsl_text = AdvancedNLToDSL().convert(nl_text)
    except NLParseError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("=== Generated DSL ===")
    print(dsl_text)

    if args.compile:
        compiler = CHACompiler()
        try:
            zip_bytes = compiler.compile(dsl_text, version=args.version)
        except CompileError as e:
            print(f"\nCompilation failed:", file=sys.stderr)
            for err in e.errors:
                print(f"  [{err.severity}] {err.message}", file=sys.stderr)
            sys.exit(1)
        output = args.output or os.path.splitext(os.path.basename(args.input))[0] + ".zip"
        with open(output, 'wb') as f:
            f.write(zip_bytes)
        print(f"\nGenerated: {output} ({len(zip_bytes)} bytes)")
    elif args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(dsl_text)
        print(f"\nDSL written to: {args.output}")


def main():
    parser = argparse.ArgumentParser(description="Ericsson CHA Configuration Compiler")
    sub = parser.add_subparsers(dest="command")

    # compile
    p = sub.add_parser("compile", help="Compile DSL to CHA import ZIP")
    p.add_argument("input", help="Input DSL file")
    p.add_argument("-o", "--output", help="Output ZIP file path")
    p.add_argument("--version", default="1.0.0", help="Config version (default: 1.0.0)")

    # batch
    p = sub.add_parser("batch", help="Compile all DSL files in a folder into one CHA package")
    p.add_argument("input", help="Input folder containing .dsl files")
    p.add_argument("-o", "--output", help="Output ZIP file path")
    p.add_argument("--version", default="1.0.0", help="Config version (default: 1.0.0)")

    # decompile
    p = sub.add_parser("decompile", help="Decompile CHA ZIP to DSL (first function)")
    p.add_argument("input", help="Input CHA ZIP file")
    p.add_argument("-o", "--output", help="Output DSL file path")

    # export
    p = sub.add_parser("export", help="Export ALL functions from CHA ZIP to individual DSL files")
    p.add_argument("input", help="Input CHA ZIP file")
    p.add_argument("-o", "--output", help="Output directory (default: exported_dsl)")

    # diff
    p = sub.add_parser("diff", help="Compare two CHA exports and show differences")
    p.add_argument("file_a", help="First CHA ZIP (before)")
    p.add_argument("file_b", help="Second CHA ZIP (after)")

    # validate
    p = sub.add_parser("validate", help="Validate a DSL file")
    p.add_argument("input", help="Input DSL file")

    # format
    p = sub.add_parser("format", help="Auto-format a DSL file")
    p.add_argument("input", help="Input DSL file")
    p.add_argument("-o", "--output", help="Output file path")
    p.add_argument("-i", "--inplace", action="store_true", help="Format in-place")

    # xml
    p = sub.add_parser("xml", help="Generate XML from DSL (without packaging)")
    p.add_argument("input", help="Input DSL file")
    p.add_argument("-o", "--output", help="Output XML file path")

    # english
    p = sub.add_parser("english", help="Convert English rules to DSL and optionally compile")
    p.add_argument("input", help="Input text file with English rules")
    p.add_argument("-o", "--output", help="Output file path (DSL or ZIP)")
    p.add_argument("--compile", action="store_true", help="Also compile to CHA ZIP")
    p.add_argument("--version", default="1.0.0", help="Config version (default: 1.0.0)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmds = {
        "compile": cmd_compile, "batch": cmd_batch, "decompile": cmd_decompile,
        "export": cmd_export, "diff": cmd_diff, "validate": cmd_validate,
        "format": cmd_format, "xml": cmd_xml, "english": cmd_english,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
