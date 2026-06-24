"""CHA Dynamic Function Compiler - Web Interface."""
import sys, os, io, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flask import Flask, render_template, request, jsonify, send_file
from cha_compiler import CHACompiler, CompileError
from cha_compiler.parser.nl_advanced import AdvancedNLToDSL
from cha_compiler.parser.nl_parser import NLParseError

app = Flask(__name__)
compiler = CHACompiler()
nl_parser = AdvancedNLToDSL()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/docs')
def docs():
    return render_template('docs.html')


@app.route('/prompt')
def prompt():
    return render_template('prompt.html')


@app.route('/api/convert', methods=['POST'])
def convert():
    """Convert English text to DSL."""
    data = request.get_json()
    text = data.get('text', '')
    coba_lookups = data.get('cobaLookups', [])  # [{spec, list, column, key, searchType}]

    try:
        dsl = nl_parser.convert(text)

        # Post-process: replace table URIs with proper COBA URIs from user input
        for lookup in coba_lookups:
            spec = lookup.get('spec', '')
            lst = lookup.get('list', '')
            column = lookup.get('column', '')
            key = lookup.get('key', '')
            search_type = lookup.get('searchType', 'EXACT_MATCH')
            proper_uri = f'rmref://coba/globalListSpecification/{spec}/globalList/{lst}'
            # Replace any LOOKUP with matching key/column with the proper URI
            old_pattern = f'key={key} search='
            if old_pattern in dsl:
                import re
                dsl = re.sub(
                    rf'IF LOOKUP table="[^"]*" column="{re.escape(column)}" key={re.escape(key)} search=\w+',
                    f'IF LOOKUP table="{proper_uri}" column="{column}" key={key} search={search_type}',
                    dsl
                )

        return jsonify({"success": True, "dsl": dsl})
    except NLParseError as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/compile', methods=['POST'])
def compile_dsl():
    """Compile DSL to XML (preview)."""
    data = request.get_json()
    dsl = data.get('dsl', '')
    try:
        func = compiler.parse_dsl(dsl)
        errors = compiler.validate(func)
        if errors:
            return jsonify({"success": False, "error": "; ".join(e.message for e in errors)})
        xml = compiler.to_xml(func)
        return jsonify({"success": True, "xml": xml, "name": func.name})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/download', methods=['POST'])
def download():
    """Compile DSL and return ZIP for download."""
    data = request.get_json()
    dsl = data.get('dsl', '')
    version = data.get('version', '1.0.0')
    try:
        zip_bytes = compiler.compile(dsl, version=version)
        func = compiler.parse_dsl(dsl)
        encoded = base64.b64encode(zip_bytes).decode('ascii')
        return jsonify({"success": True, "zip_b64": encoded, "filename": f"{func.name}.zip"})
    except CompileError as e:
        return jsonify({"success": False, "error": str(e)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3002))
    app.run(host='0.0.0.0', port=port, debug=False)
