"""End-to-end test of the CHA Configuration Compiler."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cha_compiler import CHACompiler

compiler = CHACompiler()

# 1. Decompile original CHA export
print("=" * 60)
print("TEST 1: Decompile original CHA export")
print("=" * 60)
with open(r'docs\BusinessConfig_20260622121343152.zip', 'rb') as f:
    original_dsl = compiler.decompile(f.read())
print(original_dsl)

# 2. Re-compile the decompiled DSL
print("=" * 60)
print("TEST 2: Re-compile back to ZIP")
print("=" * 60)
zip_bytes = compiler.compile(original_dsl, version_id='1781840090468')
print(f"Generated ZIP: {len(zip_bytes)} bytes")

# 3. Verify round-trip
print("\n" + "=" * 60)
print("TEST 3: Round-trip verification")
print("=" * 60)
roundtrip_dsl = compiler.decompile(zip_bytes)
print(roundtrip_dsl)
match = original_dsl == roundtrip_dsl
print(f"\nRound-trip DSL match: {match}")

# 4. Compile from scratch
print("\n" + "=" * 60)
print("TEST 4: Compile fresh DSL")
print("=" * 60)
fresh_dsl = """FUNCTION DetermineServiceScenario

INPUT
    serviceType : LongNumber
    roleOfNode : IntegerNumber

OUTPUT
    serviceScenario : String

RULE

IF serviceType == 6
    SET serviceScenario = "Forwarding"
    EXIT

IF roleOfNode == 0
    SET serviceScenario = "MobileOriginating"
    EXIT

IF roleOfNode == 1
    SET serviceScenario = "MobileTerminating"
    EXIT
"""
zip_bytes = compiler.compile(fresh_dsl)
print(f"Generated ZIP: {len(zip_bytes)} bytes")
print(f"Decompiled back:")
print(compiler.decompile(zip_bytes))

# 5. Test validation failure
print("=" * 60)
print("TEST 5: Validation failure")
print("=" * 60)
bad_dsl = """FUNCTION Broken

RULE

SET x = "hello"
"""
func = compiler.parse_dsl(bad_dsl)
errors = compiler.validate(func)
for e in errors:
    print(f"  [{e.severity}] {e.message}")

print("\nAll tests complete.")
