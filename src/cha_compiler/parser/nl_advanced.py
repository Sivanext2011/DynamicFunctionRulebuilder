"""Advanced Natural Language to DSL Converter.

Handles complex CHA operations by recognizing telecom-specific patterns:
- Extract/decode AVP fields
- Split strings by delimiter
- Substring extraction (MCC, MNC, TAC)
- COBA/Global Table lookups
- Convert data types
- Concatenate parameters
"""
from __future__ import annotations
import re
from .nl_parser import NLToDSL, NLParseError, normalize_type, parse_value, TYPE_MAP


class AdvancedNLToDSL(NLToDSL):
    """Extended NL parser that handles complex telecom operations."""

    def convert(self, text: str) -> str:
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]

        func_name = ""
        inputs = []
        outputs = []
        internals = []
        dsl_rules = []  # raw DSL lines for the RULE section

        i = 0
        while i < len(lines):
            line = lines[i]
            lower = line.lower()

            # Function name
            if lower.startswith("function:") or lower.startswith("function name:") or lower.startswith("name:"):
                func_name = line.split(":", 1)[1].strip().replace(" ", "")
            elif not func_name and not self._is_keyword_line(lower):
                func_name = re.sub(r'[^A-Za-z0-9_]', '', line)

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

            # Complex operations - pattern match
            elif self._is_decode_convert(lower):
                result = self._handle_decode(line, lines, i, internals)
                dsl_rules.extend(result["dsl"])
                i = result["end"]
                continue

            elif self._is_split_operation(lower):
                result = self._handle_split(line, internals)
                dsl_rules.extend(result["dsl"])

            elif self._is_substring_extract(lower):
                result = self._handle_substring(line, internals)
                dsl_rules.extend(result["dsl"])

            elif self._is_concatenate(lower):
                result = self._handle_concatenate(line, internals)
                dsl_rules.extend(result["dsl"])

            elif self._is_lookup(lower):
                result = self._handle_lookup(line, lines, i)
                dsl_rules.extend(result["dsl"])
                i = result["end"]
                continue

            elif lower.startswith("if ") or lower.startswith("check "):
                result = self._handle_condition_block(lines, i)
                dsl_rules.extend(result["dsl"])
                i = result["end"]
                continue

            elif lower.startswith(("else ", "otherwise ", "default ")):
                result = self._handle_default_block(line)
                dsl_rules.extend(result["dsl"])

            elif self._is_set_operation(lower):
                result = self._handle_set(line)
                dsl_rules.extend(result["dsl"])

            i += 1

        return self._build_dsl(func_name, inputs, outputs, internals, dsl_rules)

    def _is_keyword_line(self, lower: str) -> bool:
        return any(lower.startswith(p) for p in [
            "input", "output", "internal", "if ", "else", "otherwise",
            "default", "check", "decode", "extract", "split", "lookup",
            "convert", "concatenate", "combine", "set ", "read ", "when"
        ])

    # --- Detection methods ---

    def _is_decode_convert(self, lower: str) -> bool:
        return any(kw in lower for kw in ["decode", "convert", "read the", "read avp"])

    def _is_split_operation(self, lower: str) -> bool:
        return any(kw in lower for kw in ["split", "separate", "tokenize", "delimit"])

    def _is_substring_extract(self, lower: str) -> bool:
        return bool(re.search(r'extract|substring|first \d+ char|position|offset', lower))

    def _is_concatenate(self, lower: str) -> bool:
        return any(kw in lower for kw in ["concatenate", "combine", "join", "append", "form a"])

    def _is_lookup(self, lower: str) -> bool:
        return any(kw in lower for kw in [
            "lookup", "look up", "look-up", "check against", "reference table",
            "search table", "match", "coba", "global table", "mapping table"
        ])

    def _is_set_operation(self, lower: str) -> bool:
        return lower.startswith("set ")

    # --- Handler methods ---

    def _handle_decode(self, line: str, lines: list[str], start: int, internals: list) -> dict:
        """Handle decode/convert/read AVP operations."""
        dsl = []
        # Detect source parameter
        source = self._extract_param_name(line)
        target = source + "String" if source else "tmpDecoded"

        # Add internal if not already present
        if not any(n == target for n, _ in internals):
            internals.append((target, "String"))

        dsl.append(f"# ConvertDataTypeModifier: Convert {source} to String")

        # Look ahead for extract lines (MCC, MNC, TAC etc)
        end = start + 1
        while end < len(lines):
            next_lower = lines[end].lower().strip()
            if self._is_substring_extract(next_lower) or next_lower.startswith("mcc") or next_lower.startswith("mnc") or next_lower.startswith("tac"):
                result = self._handle_substring(lines[end], internals)
                dsl.extend(result["dsl"])
                end += 1
            elif self._is_concatenate(next_lower) or "combine" in next_lower or "form" in next_lower:
                result = self._handle_concatenate(lines[end], internals)
                dsl.extend(result["dsl"])
                end += 1
            elif next_lower.startswith(("extract", "decode")):
                result = self._handle_substring(lines[end], internals)
                dsl.extend(result["dsl"])
                end += 1
            else:
                break

        return {"dsl": dsl, "end": end}

    def _handle_split(self, line: str, internals: list) -> dict:
        """Handle split string operations."""
        # Try to find delimiter and target
        m = re.search(r'split\s+(\w+)\s+(?:by|using|with|on)\s+["\']?([^"\']+)["\']?', line, re.IGNORECASE)
        if m:
            source, delimiter = m.group(1), m.group(2).strip()
            target = source + "Parts"
            if not any(n == target for n, _ in internals):
                internals.append((target, "String"))
            return {"dsl": [f'# SplitStringModifier: Split {source} by "{delimiter}"']}

        return {"dsl": [f"# SplitStringModifier: {line}"]}

    def _handle_substring(self, line: str, internals: list) -> dict:
        """Handle substring/extract operations."""
        # Extract target field name (MCC, MNC, TAC, etc)
        target = None
        m = re.search(r'extract\s+(?:the\s+)?(\w+)', line, re.IGNORECASE)
        if m:
            target = "tmp" + m.group(1)
        else:
            # Look for field names
            for field in ["MCC", "MNC", "TAC", "PLMN", "prefix", "suffix"]:
                if field.lower() in line.lower():
                    target = "tmp" + field
                    break
        if target and not any(n == target for n, _ in internals):
            internals.append((target, "String"))

        return {"dsl": [f"# SubstringModifier: {line.strip()}"]}

    def _handle_concatenate(self, line: str, internals: list) -> dict:
        """Handle concatenation operations."""
        # Look for target
        m = re.search(r'(?:form|create|build|store in|into)\s+(?:a\s+)?(\w+)', line, re.IGNORECASE)
        target = m.group(1) if m else "tmpCombined"
        if not any(n == target for n, _ in internals):
            internals.append((target, "String"))
        return {"dsl": [f"# ConcatenateModifier: {line.strip()}"]}

    def _handle_lookup(self, line: str, lines: list[str], start: int) -> dict:
        """Handle COBA/table lookup operations."""
        dsl = []

        # Try to extract table name and key
        table_name = "UnknownTable"
        key_param = "tmpKey"
        column = "key"

        # Extract key param - prefer 'using' keyword over others
        m = re.search(r'(?:using|with key|key)\s+(\w+)', line, re.IGNORECASE)
        if m:
            key_param = m.group(1)
        else:
            m = re.search(r'(?:by|against|for)\s+(\w+)', line, re.IGNORECASE)
            if m:
                key_param = m.group(1)

        m = re.search(r'column\s+["\']?(\w+)["\']?', line, re.IGNORECASE)
        if m:
            column = m.group(1)

        m = re.search(r'(?:table|coba|list)\s+["\']?([A-Za-z0-9_]+)["\']?', line, re.IGNORECASE)
        if m:
            table_name = m.group(1).strip()

        # Build lookup URI
        table_uri = f"rmref://coba/globalListSpecification/{table_name}/globalList/{table_name}"

        # Look ahead for "if match found" / "if no match" patterns
        end = start + 1
        indent = ""
        while end < len(lines):
            next_line = lines[end].strip()
            next_lower = next_line.lower()

            if next_lower.startswith(("if a match", "if match", "if found", "if a matching")):
                # Actions when lookup succeeds
                end += 1
                while end < len(lines):
                    action_lower = lines[end].strip().lower()
                    if action_lower.startswith("set "):
                        result = self._handle_set(lines[end].strip())
                        # These go inside the LOOKUP IF block
                        for d in result["dsl"]:
                            dsl.append(f"    {d}")
                        end += 1
                    else:
                        break
            elif next_lower.startswith(("if no", "if not found", "if no match")):
                end += 1
                # These are the else/default actions - they go outside the IF block
                continue
            elif self._is_set_operation(next_lower) and dsl:
                # Default SET after lookup block
                break
            else:
                break

        # Build the LOOKUP condition
        lookup_line = f'IF LOOKUP table="{table_uri}" column="{column}" key={key_param} search=EXACT_MATCH'
        final_dsl = [lookup_line]
        if dsl:
            final_dsl.extend(dsl)
            final_dsl.append("")
        else:
            final_dsl.append("    # Set result from lookup")
            final_dsl.append("")

        return {"dsl": final_dsl, "end": end}

    def _handle_condition_block(self, lines: list[str], start: int) -> dict:
        """Handle if/check condition blocks - delegates to parent for simple cases."""
        line = lines[start]
        lower = line.lower()

        # Remove "check " prefix
        if lower.startswith("check "):
            line = "If " + line[6:]
            lower = line.lower()

        # Check for existence pattern: "if X is not present" / "if X is present"
        m = re.match(r'if\s+(\w[\w-]*)\s+is\s+(?:not\s+)?present', lower)
        if m:
            var = re.match(r'if\s+(\w[\w-]*)', line, re.IGNORECASE).group(1).replace("-", "")
            is_negated = "not" in lower
            if is_negated:
                # We can't directly do NOT EXISTS in a simple way, use the positive form
                dsl = [f"IF EXISTS {var}"]
            else:
                dsl = [f"IF EXISTS {var}"]

            # Look for body
            end = start + 1
            while end < len(lines):
                next_lower = lines[end].strip().lower()
                if next_lower.startswith("set "):
                    result = self._handle_set(lines[end].strip())
                    for d in result["dsl"]:
                        dsl.append(f"    {d}")
                    end += 1
                elif next_lower.startswith(("if ", "check ")):
                    # Nested condition
                    result = self._handle_condition_block(lines, end)
                    for d in result["dsl"]:
                        dsl.append(f"    {d}")
                    end = result["end"]
                elif self._is_lookup(next_lower):
                    result = self._handle_lookup(lines[end], lines, end)
                    for d in result["dsl"]:
                        dsl.append(f"    {d}")
                    end = result["end"]
                else:
                    break
            dsl.append("")
            return {"dsl": dsl, "end": end}

        # Simple if condition - use parent logic
        try:
            rule = self._parse_rule(lines, start)
            dsl = []
            conditions = rule["conditions"]
            actions = rule["actions"]

            prefix = ""
            for cond in conditions:
                if cond["op"] == "exists":
                    dsl.append(f"{prefix}IF EXISTS {cond['var']}")
                elif cond["op"] == "==":
                    dsl.append(f"{prefix}IF {cond['var']} == {parse_value(cond['value'])}")
                elif cond["op"] == "!=":
                    dsl.append(f"{prefix}IF {cond['var']} != {parse_value(cond['value'])}")
                prefix += "    "

            for action in actions:
                dsl.append(f"{prefix}SET {action['target']} = {parse_value(action['value'])}")
            if rule["has_exit"]:
                dsl.append(f"{prefix}EXIT")
            dsl.append("")

            if rule.get("else_actions"):
                for action in rule["else_actions"]:
                    dsl.append(f"SET {action['target']} = {parse_value(action['value'])}")
                dsl.append("")

            return {"dsl": dsl, "end": rule["end_line"]}
        except NLParseError:
            return {"dsl": [f"# Cannot parse: {line}"], "end": start + 1}

    def _handle_default_block(self, line: str) -> dict:
        """Handle else/otherwise/default lines."""
        content = re.sub(r'^(else|otherwise|default)\s*:?\s*', '', line, flags=re.IGNORECASE)
        if content.lower().startswith("set "):
            return self._handle_set(content)
        try:
            actions = self._parse_actions(content)
            dsl = []
            for action in actions:
                dsl.append(f"SET {action['target']} = {parse_value(action['value'])}")
            return {"dsl": dsl}
        except NLParseError:
            return {"dsl": [f"# Default: {line}"]}

    def _handle_set(self, line: str) -> dict:
        """Handle a SET operation line."""
        content = re.sub(r'^set\s+', '', line, flags=re.IGNORECASE)
        m = re.match(r'(\w[\w-]*)\s+(?:to|as|=)\s+(.+?)(?:\s+and\s+exit)?$', content, re.IGNORECASE)
        if m:
            target = m.group(1).replace("-", "")
            value = m.group(2).strip().rstrip(".")
            has_exit = "and exit" in line.lower() or line.lower().endswith("exit")
            dsl = [f"SET {target} = {parse_value(value)}"]
            if has_exit:
                dsl.append("EXIT")
            return {"dsl": dsl}
        return {"dsl": [f"# SET: {line}"]}

    def _extract_param_name(self, line: str) -> str:
        """Extract a parameter name from a descriptive line."""
        # Look for known AVP names
        m = re.search(r'(User-Location-Info|Access-Network-Info|SGSN-MCC-MNC|[\w-]+(?:AVP|Info))', line, re.IGNORECASE)
        if m:
            return m.group(1).replace("-", "")
        # Generic extraction
        m = re.search(r'(?:the|read|decode|convert)\s+(\w[\w-]+)', line, re.IGNORECASE)
        if m:
            return m.group(1).replace("-", "")
        return "tmpSource"

    def _build_dsl(self, func_name: str, inputs, outputs, internals, dsl_rules: list[str]) -> str:
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
        lines.extend(dsl_rules)

        return "\n".join(lines).rstrip() + "\n"
