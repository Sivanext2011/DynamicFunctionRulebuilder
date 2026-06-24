# Ericsson CHA Configuration Compiler

A production-grade compiler that generates Ericsson CHA configuration import packages from a simplified DSL.

## Architecture

```
DSL Text
   ↓
DSL Parser (parser/dsl_parser.py)
   ↓
Object Model (models/dynamic_function.py)
   ↓
Validator (validator.py)
   ↓
XML Serializer (serializer/xml_serializer.py)
   ↓
Package Builder (package_builder/builder.py)
   ↓
CHA Import ZIP
```

Round-trip (decompilation):
```
CHA Export ZIP
   ↓
XML Parser (serializer/xml_parser.py)
   ↓
Object Model
   ↓
DSL Decompiler (parser/dsl_decompiler.py)
   ↓
DSL Text
```

## Usage

### Compile DSL to CHA ZIP
```bash
python cha_compile.py compile examples/DetermineServiceScenario.dsl -o output.zip
```

### Decompile CHA ZIP to DSL
```bash
python cha_compile.py decompile path/to/cha-export.zip
```

### Validate DSL
```bash
python cha_compile.py validate examples/DetermineServiceScenario.dsl
```

### Generate XML only (for inspection)
```bash
python cha_compile.py xml examples/DetermineServiceScenario.dsl
```

## DSL Syntax

```
FUNCTION <Name>

INPUT
    <paramName> : <DataType>

OUTPUT
    <paramName> : <DataType>

INTERNAL
    <paramName> : <DataType>

RULE

IF <condition>
    <statements>

SET <target> = <value>
EXIT
BREAK
```

### Supported Data Types
- String, IntegerNumber, LongNumber, Boolean
- StringList, IntegerNumberList, LongNumberList
- Enumerated, OctetString, DateTime
- AddressString, AddressStringList, Measurement

### Conditions
- Comparison: `variable == value`, `!=`, `>`, `>=`, `<`, `<=`
- Existence: `EXISTS variable`
- Boolean: `variable` or `NOT variable`
- Values can be: numeric literals, `"string literals"`, or parameter references

### Modifiers
- `SET target = value` → SetDataModifier
- `EXIT` → ExitModifier
- `BREAK` → BreakIterationModifier

## Reverse Engineering: CHA Package Structure

### Outer ZIP
```
<filename>.zip
├── manifest.json                    (outer manifest)
└── cha-business-config-{ts}.zip    (inner ZIP)
```

#### Outer manifest.json
```json
{
  "configurations": [{
    "configName": "DynamicFunctions",
    "tpgName": "CHA",
    "userName": "",
    "fileName": "cha-business-config-{timestamp}.zip",
    "contentType": "application/zip",
    "timeStamp": "{timestamp}",
    "details": [{
      "configType": "dynamicfunctions",
      "subConfigType": "DynamicFunctions",
      "selectedConfig": [{"configName": "<name>", "modifiedDate": "<ISO8601>"}]
    }]
  }],
  "checksum": "<SHA-256 of inner zip bytes>",
  "softwareVersion": "2.51.1.2",
  "hostname": "<hostname>"
}
```

### Inner ZIP
```
cha-business-config-{ts}.zip
├── META-INF/manifest.json
└── DynamicFunctions/{versionId}/DynamicFunctions#{name}.xml
```

#### Inner META-INF/manifest.json
```json
{
  "configurations": [{
    "configName": "DynamicFunctions",
    "tpgName": "CHA",
    "capabilities": [],
    "configInstances": ["{name}::{versionId}"],
    "fileName": "cha-business-config.zip",
    "contentType": "application/zip",
    "timeStamp": "{versionId}"
  }],
  "entities": [{
    "primaryEntity": {
      "name": "DynamicFunctions/{versionId}/DynamicFunctions#{name}.xml",
      "type": "DynamicFunctions",
      "versionIdentifier": "{versionId}"
    },
    "dependentEntities": []
  }],
  "activeFunctionControlIds": [...],
  "releaseLevel": "1.999.2",
  "chksum": "<SHA-256>",
  "schemaVersions": [{"name": "Resource", "version": "2.0"}]
}
```

### Checksum Algorithm
- **Algorithm**: SHA-256
- **Outer checksum**: Computed over the raw bytes of the inner ZIP file
- **Inner chksum**: Present in inner manifest (purpose: content integrity)

## Project Structure

```
src/cha_compiler/
├── __init__.py
├── compiler.py              # Main facade
├── validator.py             # Validation layer
├── models/
│   ├── __init__.py
│   └── dynamic_function.py  # Domain object model
├── parser/
│   ├── __init__.py
│   ├── dsl_parser.py        # DSL → Object Model
│   └── dsl_decompiler.py    # Object Model → DSL
├── serializer/
│   ├── __init__.py
│   ├── xml_serializer.py    # Object Model → XML
│   └── xml_parser.py        # XML → Object Model
└── package_builder/
    ├── __init__.py
    └── builder.py           # Object Model → CHA ZIP
```

## Extensibility

The architecture supports adding new modules without redesign:
- New modifier types: Add to models and update parser/serializer
- NES, Service Contexts, Global Tables: Add new model classes and builders
- New DSL constructs: Extend DSL parser grammar
