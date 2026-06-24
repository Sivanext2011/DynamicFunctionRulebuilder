"""Natural Language to DSL Converter.

Converts simple English rule descriptions into CHA DSL syntax.

Supported patterns:
- "input: <name> (<type>)" or "input <name> as <type>"
- "output: <name> (<type>)"
- "internal: <name> (<type>)"
- "if <var> is/equals/= <value> [and <var> is/equals <value>] then set <target> to/as/= <value>"
- "else set <target> to/as/= <value>"
- "otherwise set <target> to/as/= <value>"
- "default <target> = <value>"
- "exit after" / "and exit" / "stop"
"""
from __future__ import annotations
import re


class NLParseError(Exception):
    pass


# Data type aliases
TYPE_MAP = {
    "string": "String", "str": "String", "text": "String",
    "int": "IntegerNumber", "integer": "IntegerNumber", "integernumber": "IntegerNumber",
    "long": "LongNumber", "longnumber": "LongNumber",
    "bool": "Boolean", "boolean": "Boolean",
    "stringlist": "StringList", "string list": "StringList",
    "integerlist": "IntegerNumberList", "integernumberlist": "IntegerNumberList",
    "longlist": "LongNumberList", "longnumberlist": "LongNumberList",
    "octetstring": "OctetString", "octet": "OctetString",
    "addressstring": "AddressString", "address": "AddressString",
    "datetime": "DateTime", "measurement": "Measurement",
    "enumerated": "Enumerated", "enum": "Enumerated",
}


def normalize_type(raw: str) -> str:
    """Resolve a user-typed data type to a valid CHA type."""
    key = raw.strip().lower().replace(" ", "")
    if key in TYPE_MAP:
        return TYPE_MAP[key]
    # Try exact match (case-insensitive)
    for v in TYPE_MAP.values():
        if v.lower() == key:
            return v
    raise NLParseError(f"Unknown data type: '{raw}'. Valid types: String, IntegerNumber, LongNumber, Boolean, StringList, etc.")


def parse_value(val: str) -> str:
    """Format a value for DSL - add quotes if it's not numeric."""
    val = val.strip().strip("'\"")
    try:
        int(val)
        return val
    except ValueError:
        return f'"{val}"'


class NLToDSL:
    """Converts natural language rules to CHA DSL."""

    def convert(self, text: str) -> str:
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]

        func_name = ""
        inputs = []
        outputs = []
        internals = []
        rules = []

        i = 0
        while i < len(lines):
            line = lines[i]
            lower = line.lower()

            # Function name
            if lower.startswith("function:") or lower.startswith("function name:") or lower.startswith("name:"):
                func_name = line.split(":", 1)[1].strip()
            elif not func_name and not any(lower.startswith(p) for p in ["input", "output", "internal", "if ", "else", "otherwise", "default"]):
                # First non-keyword line could be the function name
                func_name = line.replace(" ", "")

            # Parameters
            elif lower.startswith("input"):
                params = self._parse_params(line, "input")
                inputs.extend(params)
            elif lower.startswith("output"):
                params = self._parse_params(line, "output")
                outputs.extend(params)
            elif lower.startswith("internal"):
                params = self._parse_params(line, "internal")
                internals.extend(params)

            # Rules
            elif lower.startswith("if "):
                rule = self._parse_rule(lines, i)
                rules.append(rule)
                # Skip lines consumed by this rule
                i = rule["end_line"]
                continue

            elif lower.startswith(("else ", "otherwise ", "default ")):
                rule = self._parse_default(line)
                rules.append(rule)

            i += 1

        return self._generate_dsl(func_name, inputs, outputs, internals, rules)

    def _parse_params(self, line: str, prefix: str) -> list[tuple[str, str]]:
        """Parse parameter declarations from a line."""
        # Remove the prefix word(s)
        content = re.sub(r'^(input|output|internal)\s*(parameters?|params?)?[:\s]*', '', line, flags=re.IGNORECASE)

        params = []
        # Split by comma or "and"
        parts = re.split(r'\s*[,;]\s*|\s+and\s+', content)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Match patterns: "name (type)", "name:type", "name as type", "name - type"
            m = re.match(r'([A-Za-z_][\w-]*)\s*[\(:]\s*(\w+[\s\w]*?)\s*\)?$', part)
            if not m:
                m = re.match(r'([A-Za-z_][\w-]*)\s+(?:as|is)\s+(\w+[\s\w]*?)$', part, re.IGNORECASE)
            if not m:
                m = re.match(r'([A-Za-z_][\w-]*)\s*[-–]\s*(\w+[\s\w]*?)$', part)
            if m:
                name = m.group(1).strip().replace("-", "")
                dtype = normalize_type(m.group(2))
                params.append((name, dtype))
            else:
                raise NLParseError(f"Cannot parse parameter from: '{part}'. Expected format: 'name (type)' or 'name as type'")
        return params

    def _parse_rule(self, lines: list[str], start: int) -> dict:
        """Parse an IF rule with conditions and actions."""
        line = lines[start]
        lower = line.lower()

        # Remove "if " prefix
        content = line[3:].strip()

        # Split into condition and action parts
        # Look for "then", "set", ":" as separators
        cond_part, action_part = self._split_condition_action(content)

        conditions = self._parse_conditions(cond_part)
        actions = self._parse_actions(action_part)

        # Check for "and exit" / "exit" / "stop" in the action
        has_exit = False
        exit_words = ["and exit", "exit", "stop", "and stop"]
        for ew in exit_words:
            if ew in action_part.lower():
                has_exit = True
                # Remove exit word from actions
                for a in actions:
                    a["value"] = re.sub(r'\s*(and\s+)?(exit|stop)\s*$', '', a["value"], flags=re.IGNORECASE)
                break

        # Check next line for "else" belonging to this if
        end = start + 1
        else_actions = []
        if end < len(lines):
            next_lower = lines[end].lower().strip()
            if next_lower.startswith(("else ", "otherwise ")):
                else_content = re.sub(r'^(else|otherwise)\s*:?\s*', '', lines[end], flags=re.IGNORECASE)
                else_actions = self._parse_actions(else_content)
                has_else_exit = any(w in else_content.lower() for w in ["and exit", "exit", "stop"])
                end += 1

        return {
            "type": "if",
            "conditions": conditions,
            "actions": actions,
            "has_exit": has_exit,
            "else_actions": else_actions,
            "end_line": end,
        }

    def _split_condition_action(self, content: str) -> tuple[str, str]:
        """Split a rule into condition and action parts."""
        # Try "then" separator
        m = re.split(r'\s+then\s+', content, maxsplit=1, flags=re.IGNORECASE)
        if len(m) == 2:
            return m[0], m[1]
        # Try "set" as separator
        m = re.split(r'\s+set\s+', content, maxsplit=1, flags=re.IGNORECASE)
        if len(m) == 2:
            return m[0], "set " + m[1]
        # Try colon
        if ":" in content:
            parts = content.split(":", 1)
            return parts[0], parts[1]
        raise NLParseError(f"Cannot find action in rule: '{content}'. Use 'then' or ':' to separate condition from action.")

    def _parse_conditions(self, cond_str: str) -> list[dict]:
        """Parse conditions from a string like 'x is 5 and y equals 10'."""
        # Split by "and"
        parts = re.split(r'\s+and\s+', cond_str, flags=re.IGNORECASE)
        conditions = []
        for part in parts:
            part = part.strip()
            # Match: var is/equals/==/= value
            m = re.match(r'([A-Za-z_][\w-]*)\s+(?:is|equals?|==?|is equal to)\s+(.+)$', part, re.IGNORECASE)
            if m:
                var = m.group(1).strip().replace("-", "")
                val = m.group(2).strip()
                conditions.append({"var": var, "op": "==", "value": val})
            # Match: var exists
            elif re.match(r'([A-Za-z_][\w-]*)\s+exists', part, re.IGNORECASE):
                var = re.match(r'([A-Za-z_][\w-]*)', part).group(1).replace("-", "")
                conditions.append({"var": var, "op": "exists", "value": None})
            # Match: var != value
            elif re.match(r'([A-Za-z_][\w-]*)\s+(?:is not|!=|not equals?)\s+(.+)$', part, re.IGNORECASE):
                m2 = re.match(r'([A-Za-z_][\w-]*)\s+(?:is not|!=|not equals?)\s+(.+)$', part, re.IGNORECASE)
                conditions.append({"var": m2.group(1).replace("-", ""), "op": "!=", "value": m2.group(2).strip()})
            else:
                raise NLParseError(f"Cannot parse condition: '{part}'. Expected format: 'variable is value' or 'variable equals value'")
        return conditions

    def _parse_actions(self, action_str: str) -> list[dict]:
        """Parse actions from a string like 'set target to value'."""
        actions = []
        # Remove "then" prefix if present
        action_str = re.sub(r'^then\s+', '', action_str, flags=re.IGNORECASE)

        # Split multiple set actions by "and set" or comma
        parts = re.split(r'\s*(?:,\s*(?:and\s+)?|(?:and\s+))set\s+', action_str, flags=re.IGNORECASE)

        for j, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            # Remove leading "set" from first part
            if j == 0:
                part = re.sub(r'^set\s+', '', part, flags=re.IGNORECASE)

            # Match: target to/as/= value
            m = re.match(r'([A-Za-z_][\w-]*)\s+(?:to|as|=)\s+(.+?)(?:\s+and\s+exit|\s+exit|\s+stop)?$', part, re.IGNORECASE)
            if m:
                target = m.group(1).strip().replace("-", "")
                value = m.group(2).strip().rstrip(".")
                actions.append({"target": target, "value": value})
            else:
                raise NLParseError(f"Cannot parse action: '{part}'. Expected format: 'set target to value'")
        return actions

    def _parse_default(self, line: str) -> dict:
        """Parse a default/else/otherwise line."""
        content = re.sub(r'^(else|otherwise|default)\s*:?\s*', '', line, flags=re.IGNORECASE)
        actions = self._parse_actions(content)
        return {"type": "default", "actions": actions}

    def _generate_dsl(self, func_name: str, inputs, outputs, internals, rules) -> str:
        if not func_name:
            func_name = "GeneratedFunction"

        lines = [f"FUNCTION {func_name}", ""]

        if inputs:
            lines.append("INPUT")
            for name, dtype in inputs:
                lines.append(f"    {name} : {dtype}")
            lines.append("")

        if outputs:
            lines.append("OUTPUT")
            for name, dtype in outputs:
                lines.append(f"    {name} : {dtype}")
            lines.append("")

        if internals:
            lines.append("INTERNAL")
            for name, dtype in internals:
                lines.append(f"    {name} : {dtype}")
            lines.append("")

        lines.append("RULE")
        lines.append("")

        for rule in rules:
            if rule["type"] == "if":
                self._emit_if_rule(rule, lines, indent=0)
            elif rule["type"] == "default":
                for action in rule["actions"]:
                    lines.append(f"SET {action['target']} = {parse_value(action['value'])}")

        return "\n".join(lines).rstrip() + "\n"

    def _emit_if_rule(self, rule: dict, lines: list[str], indent: int):
        conditions = rule["conditions"]
        actions = rule["actions"]

        # Nest multiple conditions
        prefix = "    " * indent
        for i, cond in enumerate(conditions):
            if cond["op"] == "exists":
                lines.append(f"{prefix}IF EXISTS {cond['var']}")
            elif cond["op"] == "==":
                lines.append(f"{prefix}IF {cond['var']} == {parse_value(cond['value'])}")
            elif cond["op"] == "!=":
                lines.append(f"{prefix}IF {cond['var']} != {parse_value(cond['value'])}")
            prefix = "    " * (indent + i + 1)

        # Actions at deepest indent
        for action in actions:
            lines.append(f"{prefix}SET {action['target']} = {parse_value(action['value'])}")

        if rule["has_exit"]:
            lines.append(f"{prefix}EXIT")

        # Else
        if rule.get("else_actions"):
            else_prefix = "    " * indent
            lines.append("")
            for action in rule["else_actions"]:
                lines.append(f"SET {action['target']} = {parse_value(action['value'])}")

        lines.append("")
