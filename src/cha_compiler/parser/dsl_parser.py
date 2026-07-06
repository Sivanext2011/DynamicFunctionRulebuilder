"""DSL Parser: Converts CHA DSL text into DynamicFunction object model.

Supported DSL keywords for all CHA-documented elements:

Conditions:
    IF <var> == <value>              → CompareDataCondition
    IF <var> != <value>              → CompareDataCondition
    IF <var> > <value>               → CompareDataCondition
    IF EXISTS <var>                  → DoesDataExistCondition
    IF <var> / IF NOT <var>          → BooleanCondition
    IF LENGTH <var> == <value>       → LengthCondition
    IF LOOKUP table=".." ...         → GlobalTableQueryCondition

Modifiers:
    SET <target> = <value>           → SetDataModifier
    EXIT                             → ExitModifier
    BREAK                            → BreakIterationModifier
    CONVERT <source> TO <target>     → ConvertDataTypeModifier
    SPLIT <source> BY <delim> INTO <target>  → SplitStringModifier
    SUBSTRING <source> <start> <end> INTO <target>  → SubstringModifier
    REPLACE <source> <regex> WITH <replacement> INTO <target>  → ReplaceStringModifier
    LENGTH <source> INTO <target>    → LengthModifier
    MATH <target> = <left> <op> <right>  → BasicMathModifier
    CONCAT <source1>, <source2> INTO <target>  → AddStringModifier (2 inputs only)
    ENUMERATE <source> INTO <target> → EnumerationModifier
    LOOKUP_SET table=".." column=".." key=<p> result=<col> target=<t> default=<d>  → GlobalTableQueryModifier
"""
from __future__ import annotations
import re
from ..models import (
    DataType, ParameterTemplate, CompareOperator,
    Parameter, Property, Condition, Modifier, Node, DynamicFunction,
)


class DSLParseError(Exception):
    pass


class DSLParser:
    """Parses the CHA DSL into a DynamicFunction object model."""

    def parse(self, text: str) -> DynamicFunction:
        lines = [l.rstrip() for l in text.strip().splitlines()]
        pos = 0

        pos, name = self._parse_function_header(lines, pos)
        func = DynamicFunction(name=name, description=name)

        while pos < len(lines):
            line = lines[pos].strip()
            if not line:
                pos += 1
                continue
            if line == "INPUT":
                pos = self._parse_parameters(lines, pos + 1, func, ParameterTemplate.InputParameter)
            elif line == "OUTPUT":
                pos = self._parse_parameters(lines, pos + 1, func, ParameterTemplate.OutputParameter)
            elif line == "INTERNAL":
                pos = self._parse_parameters(lines, pos + 1, func, ParameterTemplate.InternalParameter)
            elif line == "DESCRIPTION":
                pos += 1
                if pos < len(lines):
                    func.description = lines[pos].strip()
                    pos += 1
            elif line == "RULE":
                pos, func.root_node = self._parse_rule(lines, pos + 1, func)
            else:
                pos += 1

        return func

    def _parse_function_header(self, lines, pos):
        while pos < len(lines):
            line = lines[pos].strip()
            if line.startswith("FUNCTION "):
                return pos + 1, line[9:].strip()
            pos += 1
        raise DSLParseError("No FUNCTION declaration found")

    def _parse_parameters(self, lines, pos, func, template):
        while pos < len(lines):
            line = lines[pos].strip()
            if not line:
                pos += 1
                continue
            if line in ("INPUT", "OUTPUT", "INTERNAL", "RULE", "DESCRIPTION") or line.startswith("FUNCTION "):
                break
            # "name : Type" or "name : Type [List]"
            m = re.match(r'^([\w.\-]+)\s*:\s*(\w+)(?:\s*\[(\w+)\])?$', line)
            if m:
                name, dtype, coll = m.group(1), m.group(2), m.group(3)
                try:
                    data_type = DataType(dtype)
                except ValueError:
                    raise DSLParseError(f"Unknown data type: {dtype}")
                func.parameters.append(Parameter(name=name, data_type=data_type, template=template, collection_type=coll))
            pos += 1
        return pos

    def _parse_rule(self, lines, pos, func):
        root = Node(name="RootNode")
        pos = self._parse_rule_body(lines, pos, root, func, indent_level=0)
        return pos, root

    def _parse_rule_body(self, lines, pos, parent, func, indent_level):
        while pos < len(lines):
            line = lines[pos]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                pos += 1
                continue

            current_indent = len(line) - len(line.lstrip())
            if current_indent < indent_level and stripped:
                break

            if stripped.startswith("IF "):
                pos = self._parse_if_block(lines, pos, parent, func, current_indent)
            elif stripped == "ELSE":
                break
            elif stripped.startswith("SET "):
                parent.modifiers.append(self._parse_set(stripped, func))
                pos += 1
            elif stripped == "EXIT":
                parent.modifiers.append(Modifier(name="Exit", modifier_type="ExitModifier"))
                pos += 1
            elif stripped == "BREAK":
                parent.modifiers.append(Modifier(name="Break", modifier_type="BreakIterationModifier"))
                pos += 1
            elif stripped.startswith("ITERATE "):
                pos = self._parse_iterate_block(lines, pos, parent, func, current_indent)
            elif stripped.startswith("CONVERT "):
                parent.modifiers.append(self._parse_convert(stripped))
                pos += 1
            elif stripped.startswith("SPLIT "):
                parent.modifiers.append(self._parse_split(stripped))
                pos += 1
            elif stripped.startswith("SUBSTRING "):
                parent.modifiers.append(self._parse_substring(stripped))
                pos += 1
            elif stripped.startswith("REPLACE "):
                parent.modifiers.append(self._parse_replace(stripped))
                pos += 1
            elif stripped.startswith("LENGTH "):
                parent.modifiers.append(self._parse_length_modifier(stripped))
                pos += 1
            elif stripped.startswith("MATH "):
                parent.modifiers.append(self._parse_math(stripped))
                pos += 1
            elif stripped.startswith("CONCAT "):
                parent.modifiers.append(self._parse_concat(stripped))
                pos += 1
            elif stripped.startswith("ENUMERATE "):
                parent.modifiers.append(self._parse_enumerate(stripped))
                pos += 1
            elif stripped.startswith("LOOKUP_SET "):
                parent.modifiers.append(self._parse_lookup_set(stripped))
                pos += 1
            elif stripped.startswith("OCTET_TO_HEX ") or stripped.startswith("HEX_TO_OCTET "):
                parent.modifiers.append(self._parse_octet_hex(stripped))
                pos += 1
            elif stripped.startswith("IP_TO_STRING "):
                parent.modifiers.append(self._parse_ip_to_string(stripped))
                pos += 1
            elif stripped.startswith("TBCD_TO_STRING "):
                parent.modifiers.append(self._parse_tbcd(stripped))
                pos += 1
            elif stripped.startswith("EXTRACT_BITS "):
                parent.modifiers.append(self._parse_extract_bits(stripped))
                pos += 1
            elif stripped.startswith("EXTRACT_OCTET "):
                parent.modifiers.append(self._parse_extract_octet(stripped))
                pos += 1
            elif stripped.startswith("EXTRACT_NTET "):
                parent.modifiers.append(self._parse_extract_ntet(stripped))
                pos += 1
            elif stripped.startswith("BITMASK "):
                parent.modifiers.append(self._parse_bitmask(stripped))
                pos += 1
            elif stripped.startswith("STRING_PICK "):
                parent.modifiers.append(self._parse_string_picker(stripped))
                pos += 1
            elif stripped.startswith("STRING_TO_MAP "):
                parent.modifiers.append(self._parse_string_to_map(stripped))
                pos += 1
            elif stripped.startswith("CREATE_ADDRESS "):
                parent.modifiers.append(self._parse_create_address(stripped))
                pos += 1
            elif stripped.startswith("MULTI_LOOKUP_SET "):
                parent.modifiers.append(self._parse_multi_lookup_set(stripped))
                pos += 1
            else:
                pos += 1

        return pos

    def _parse_if_block(self, lines, pos, parent, func, base_indent):
        line = lines[pos].strip()
        condition_expr = line[3:].strip()
        condition = self._parse_condition(condition_expr, func)

        node = Node(name=self._generate_node_name(condition_expr), condition=condition)
        parent.children.append(node)
        pos += 1

        body_indent = base_indent + 4
        pos = self._parse_rule_body(lines, pos, node, func, body_indent)

        if pos < len(lines) and lines[pos].strip() == "ELSE":
            pos += 1
            else_node = Node(name="Else")
            parent.children.append(else_node)
            pos = self._parse_rule_body(lines, pos, else_node, func, body_indent)

        return pos

    def _parse_iterate_block(self, lines, pos, parent, func, base_indent):
        """ITERATE <collection> AS <value> INDEX <index>"""
        line = lines[pos].strip()
        m = re.match(r'^ITERATE\s+(\w+)\s+AS\s+(\w+)\s+INDEX\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid ITERATE: {line}. Expected: ITERATE collection AS value INDEX index")

        coll, val, idx = m.group(1), m.group(2), m.group(3)
        condition = Condition(
            name=f"Iterate {coll}",
            condition_type="IteratorNode",
            properties=[
                Property(name="Collection", type="value", data_definition_name=coll),
                Property(name="IterationValue", type="value", data_definition_name=val),
                Property(name="IterationIndex", type="value", data_definition_name=idx),
            ]
        )
        node = Node(name=f"Iterate {coll}", condition=condition)
        parent.children.append(node)
        pos += 1

        body_indent = base_indent + 4
        pos = self._parse_rule_body(lines, pos, node, func, body_indent)
        return pos

    # --- Condition Parsers ---

    def _parse_condition(self, expr, func):
        # EXISTS
        m = re.match(r'^EXISTS\s+(\w+)$', expr)
        if m:
            return Condition(name=f"When {m.group(1)} exists", condition_type="DoesDataExistCondition",
                           properties=[Property(name="Data", type="value", data_definition_name=m.group(1))])

        # LENGTH condition: LENGTH var == value
        m = re.match(r'^LENGTH\s+(\w+)\s*(==|!=|>|>=|<|<=)\s*(.+)$', expr)
        if m:
            var, op_str, val = m.group(1), m.group(2), m.group(3).strip()
            op_map = {"==": "EQ", "!=": "NEQ", ">": "GT", ">=": "GTE", "<": "LT", "<=": "LTE"}
            return Condition(name=f"When length of {var} {op_str} {val}", condition_type="LengthCondition",
                           properties=[
                               Property(name="Data", type="value", data_definition_name=var),
                               Property(name="Operator", type="", constant_value=op_map[op_str]),
                               Property(name="CompareValue", type="value", constant_value=val, constant_data_type=DataType.IntegerNumber),
                           ])

        # LOOKUP
        m = re.match(r'^LOOKUP\s+(.+)$', expr)
        if m:
            return self._parse_lookup_condition(m.group(1).strip(), func)

        # Comparison
        m = re.match(r'^([\w.\-]+)\s*(==|!=|>=|<=|>|<|ENDS_WITH|STARTS_WITH|CONTAINS)\s*(.+)$', expr, re.IGNORECASE)
        if m:
            var_name, op_str, value = m.group(1), m.group(2).upper(), m.group(3).strip()
            op_map = {"==": CompareOperator.EQ, "!=": CompareOperator.NEQ,
                      ">": CompareOperator.GT, ">=": CompareOperator.GTE,
                      "<": CompareOperator.LT, "<=": CompareOperator.LTE,
                      "ENDS_WITH": CompareOperator.ENDS_WITH,
                      "STARTS_WITH": CompareOperator.STARTS_WITH,
                      "CONTAINS": CompareOperator.CONTAINS}
            compare_to_prop = self._parse_value_expression(value, func)
            compare_to_prop.name = "SourceDataCompareTo"
            return Condition(name=f"When {var_name} {op_str} {value}", condition_type="CompareDataCondition",
                           properties=[
                               Property(name="SourceDataComparable", type="value", data_definition_name=var_name),
                               Property(name="Operator", type="", constant_value=op_map[op_str].value),
                               compare_to_prop,
                           ])

        # Boolean: NOT var or var
        m = re.match(r'^(NOT\s+)?(\w+)$', expr)
        if m:
            negated, var_name = m.group(1) is not None, m.group(2)
            props = [Property(name="Data", type="value", data_definition_name=var_name)]
            if negated:
                props.append(Property(name="Negate", type="", constant_value="true"))
            return Condition(name=f"When {var_name} is {'false' if negated else 'true'}",
                           condition_type="BooleanCondition", properties=props)

        raise DSLParseError(f"Cannot parse condition: {expr}")

    def _parse_lookup_condition(self, args_str, func):
        attrs = dict(re.findall(r'(\w+)\s*=\s*"([^"]+)"', args_str))
        for m in re.finditer(r'(\w+)\s*=\s*([^\s"]+)', args_str):
            if m.group(1) not in attrs:
                attrs[m.group(1)] = m.group(2)
        return Condition(
            name=attrs.get("name", f"Lookup {attrs.get('column','')} in table"),
            condition_type="GlobalTableQueryCondition",
            properties=[
                Property(name="Table", type="value", constant_value=attrs.get("table", ""), constant_data_type=DataType.String),
                Property(name="ColumnToSearch", type="value", constant_value=attrs.get("column", ""), constant_data_type=DataType.String),
                Property(name="Key", type="value", data_definition_name=attrs.get("key", "")),
                Property(name="SearchType", type="", constant_value=attrs.get("search", "EXACT_MATCH")),
            ])

    # --- Modifier Parsers ---

    def _parse_set(self, line, func):
        m = re.match(r'^SET\s+(\w+)\s*=\s*(.+)$', line)
        if not m:
            raise DSLParseError(f"Invalid SET: {line}")
        target, value_expr = m.group(1), m.group(2).strip()
        source_prop = self._parse_value_expression(value_expr, func)
        source_prop.name = "Source"
        return Modifier(name=f"Set {target}", modifier_type="SetDataModifier",
                       properties=[source_prop, Property(name="Target", type="value", data_definition_name=target)])

    def _parse_convert(self, line):
        """CONVERT <source> TO <target>"""
        m = re.match(r'^CONVERT\s+(\w+)\s+TO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid CONVERT: {line}. Expected: CONVERT source TO target")
        return Modifier(name=f"Convert {m.group(1)} to {m.group(2)}", modifier_type="ConvertDataTypeModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="Target", type="value", data_definition_name=m.group(2)),
                       ])

    def _parse_split(self, line):
        """SPLIT <source> BY <delimiter> INTO <target>"""
        m = re.match(r'^SPLIT\s+(\w+)\s+BY\s+"([^"]+)"\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            m = re.match(r'^SPLIT\s+(\w+)\s+BY\s+(\S+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid SPLIT: {line}. Expected: SPLIT source BY \"delim\" INTO target")
        return Modifier(name=f"Split {m.group(1)}", modifier_type="SplitStringModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="Delimiter", type="value", constant_value=m.group(2), constant_data_type=DataType.String),
                           Property(name="Target", type="value", data_definition_name=m.group(3)),
                       ])

    def _parse_substring(self, line):
        """SUBSTRING <source> <start> <end> INTO <target>"""
        m = re.match(r'^SUBSTRING\s+(\w+(?:\[\w+\])?)\s+(\d+)\s+(\d+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid SUBSTRING: {line}. Expected: SUBSTRING source start end INTO target")
        source = m.group(1)
        # Handle indexed access: source[index]
        src_name, src_keys = source, None
        idx = re.match(r'^(\w+)\[(\w+)\]$', source)
        if idx:
            src_name, src_keys = idx.group(1), [idx.group(2)]
        return Modifier(name=f"Substring {src_name}", modifier_type="SubstringModifier",
                       properties=[
                           Property(name="SourceString", type="value", data_definition_name=src_name, data_definition_keys=src_keys),
                           Property(name="StartIndex", type="value", constant_value=m.group(2), constant_data_type=DataType.IntegerNumber),
                           Property(name="EndIndex", type="value", constant_value=m.group(3), constant_data_type=DataType.IntegerNumber),
                           Property(name="TargetString", type="value", data_definition_name=m.group(4)),
                       ])

    def _parse_replace(self, line):
        """REPLACE <source> <regex> WITH <replacement> INTO <target>"""
        m = re.match(r'^REPLACE\s+(\w+)\s+"([^"]+)"\s+WITH\s+"([^"]*)"\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid REPLACE: {line}. Expected: REPLACE source \"regex\" WITH \"replacement\" INTO target")
        return Modifier(name=f"Replace in {m.group(1)}", modifier_type="ReplaceStringModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="Regex", type="value", constant_value=m.group(2), constant_data_type=DataType.String),
                           Property(name="Replace", type="value", constant_value=m.group(3), constant_data_type=DataType.String),
                           Property(name="Target", type="value", data_definition_name=m.group(4)),
                       ])

    def _parse_length_modifier(self, line):
        """LENGTH <source> INTO <target>"""
        m = re.match(r'^LENGTH\s+(\w+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid LENGTH: {line}. Expected: LENGTH source INTO target")
        return Modifier(name=f"Length of {m.group(1)}", modifier_type="LengthModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="Target", type="value", data_definition_name=m.group(2)),
                       ])

    def _parse_math(self, line):
        """MATH <target> = <left> <op> <right>"""
        m = re.match(r'^MATH\s+(\w+)\s*=\s*(\w+)\s*([+\-*/])\s*(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid MATH: {line}. Expected: MATH target = left op right")
        op_map = {"+": "ADD", "-": "SUBTRACT", "*": "MULTIPLY", "/": "DIVIDE"}
        return Modifier(name=f"Math {m.group(1)}", modifier_type="BasicMathModifier",
                       properties=[
                           Property(name="LeftOperand", type="value", data_definition_name=m.group(2)),
                           Property(name="Operator", type="", constant_value=op_map.get(m.group(3), "ADD")),
                           Property(name="RightOperand", type="value", data_definition_name=m.group(4)),
                           Property(name="Target", type="value", data_definition_name=m.group(1)),
                       ])

    def _parse_concat(self, line):
        """CONCAT <source>, <addString> INTO <target> (2 inputs only, matches CHA AddStringModifier)"""
        m = re.match(r'^CONCAT\s+(.+?)\s+INTO\s+([\w.\-]+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid CONCAT: {line}. Expected: CONCAT source, addString INTO target")
        sources_str, target = m.group(1).strip(), m.group(2)
        # Split by comma
        parts = [p.strip() for p in re.split(r',', sources_str) if p.strip()]
        # Fallback: if no commas, split by space (legacy: CONCAT a b INTO t)
        if len(parts) == 1 and not parts[0].startswith('"'):
            parts = sources_str.split()
        if len(parts) != 2:
            raise DSLParseError(f"Invalid CONCAT: {line}. CHA AddStringModifier takes exactly 2 sources, got {len(parts)}")
        props = []
        for i, part in enumerate(parts, 1):
            name = "SourceString" if i == 1 else "AddString"
            if (part.startswith('"') and part.endswith('"')) or (part.startswith("'") and part.endswith("'")):
                props.append(Property(name=name, type="value", constant_value=part[1:-1], constant_data_type=DataType.String))
            else:
                props.append(Property(name=name, type="value", data_definition_name=part))
        props.append(Property(name="TargetString", type="value", data_definition_name=target))
        return Modifier(name=f"Concat into {target}", modifier_type="AddStringModifier", properties=props)

    def _parse_enumerate(self, line):
        """ENUMERATE <source> INTO <target>"""
        m = re.match(r'^ENUMERATE\s+(\w+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid ENUMERATE: {line}. Expected: ENUMERATE source INTO target")
        return Modifier(name=f"Enumerate {m.group(1)}", modifier_type="EnumerationModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="Target", type="value", data_definition_name=m.group(2)),
                       ])

    def _parse_lookup_set(self, line):
        """LOOKUP_SET table="..." column="..." key=<p> result=<col> target=<t> [default=<d>]"""
        attrs = dict(re.findall(r'(\w+)\s*=\s*"([^"]+)"', line))
        for m_iter in re.finditer(r'(\w+)\s*=\s*([^\s"]+)', line):
            if m_iter.group(1) not in attrs and m_iter.group(1) not in ("LOOKUP_SET",):
                attrs[m_iter.group(1)] = m_iter.group(2)
        key_val = attrs.get("key", "")
        target_val = attrs.get("target", "")
        props = [
            Property(name="Table", type="value", constant_value=attrs.get("table", ""), constant_data_type=DataType.String),
            Property(name="ColumnToSearch", type="value", constant_value=attrs.get("column", ""), constant_data_type=DataType.String),
            Property(name="Key", type="value", data_definition_name=key_val),
            Property(name="ColumnToReturn", type="value", constant_value=attrs.get("result", ""), constant_data_type=DataType.String),
            Property(name="Target", type="value", data_definition_name=target_val),
            Property(name="SearchType", type="", constant_value=attrs.get("search", "EXACT_MATCH")),
        ]
        if "default" in attrs:
            props.append(Property(name="DefaultValue", type="value", constant_value=attrs["default"], constant_data_type=DataType.String))
        return Modifier(name=f"Lookup and set {target_val}", modifier_type="GlobalTableQueryModifier", properties=props)

    def _parse_octet_hex(self, line):
        """OCTET_TO_HEX <source> INTO <target> / HEX_TO_OCTET <source> INTO <target>"""
        m = re.match(r'^(OCTET_TO_HEX|HEX_TO_OCTET)\s+(\w+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid: {line}")
        return Modifier(name=f"{m.group(1)} {m.group(2)}", modifier_type="OctetHexConvertModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(2)),
                           Property(name="Target", type="value", data_definition_name=m.group(3)),
                       ])

    def _parse_ip_to_string(self, line):
        """IP_TO_STRING <source> INTO <target>"""
        m = re.match(r'^IP_TO_STRING\s+(\w+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid: {line}")
        return Modifier(name=f"IP to string {m.group(1)}", modifier_type="IpAddressToStringModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="Target", type="value", data_definition_name=m.group(2)),
                       ])

    def _parse_tbcd(self, line):
        """TBCD_TO_STRING <source> <format> INTO <target>"""
        m = re.match(r'^TBCD_TO_STRING\s+(\w+)\s+(\w+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid: {line}")
        return Modifier(name=f"TBCD to string {m.group(1)}", modifier_type="TbcdToStringModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="Format", type="value", constant_value=m.group(2), constant_data_type=DataType.String),
                           Property(name="Target", type="value", data_definition_name=m.group(3)),
                       ])

    def _parse_extract_bits(self, line):
        """EXTRACT_BITS <source> <byteIndex> <bitOffset> <bitLength> INTO <target>"""
        m = re.match(r'^EXTRACT_BITS\s+(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid: {line}")
        return Modifier(name=f"Extract bits from {m.group(1)}", modifier_type="ExtractBitsModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="ByteIndex", type="value", constant_value=m.group(2), constant_data_type=DataType.IntegerNumber),
                           Property(name="BitOffset", type="value", constant_value=m.group(3), constant_data_type=DataType.IntegerNumber),
                           Property(name="BitLength", type="value", constant_value=m.group(4), constant_data_type=DataType.IntegerNumber),
                           Property(name="Target", type="value", data_definition_name=m.group(5)),
                       ])

    def _parse_extract_octet(self, line):
        """EXTRACT_OCTET <source> <startIndex> <length> INTO <target>"""
        m = re.match(r'^EXTRACT_OCTET\s+(\w+)\s+(\d+)\s+(\d+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid: {line}")
        return Modifier(name=f"Extract octet from {m.group(1)}", modifier_type="ExtractOctetModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="StartIndex", type="value", constant_value=m.group(2), constant_data_type=DataType.IntegerNumber),
                           Property(name="LengthToRead", type="value", constant_value=m.group(3), constant_data_type=DataType.IntegerNumber),
                           Property(name="Target", type="value", data_definition_name=m.group(4)),
                       ])

    def _parse_extract_ntet(self, line):
        """EXTRACT_NTET <source> <nbit> INTO <target>"""
        m = re.match(r'^EXTRACT_NTET\s+(\w+)\s+(\d+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid: {line}")
        return Modifier(name=f"Extract ntet from {m.group(1)}", modifier_type="ExtractNtetModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="Nbit", type="value", constant_value=m.group(2), constant_data_type=DataType.IntegerNumber),
                           Property(name="Target", type="value", data_definition_name=m.group(3)),
                       ])

    def _parse_bitmask(self, line):
        """BITMASK <source> <mask> INTO <target>"""
        m = re.match(r'^BITMASK\s+(\w+)\s+(\w+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid: {line}")
        return Modifier(name=f"Bitmask {m.group(1)}", modifier_type="BitMaskModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="Mask", type="value", constant_value=m.group(2), constant_data_type=DataType.String),
                           Property(name="Target", type="value", data_definition_name=m.group(3)),
                       ])

    def _parse_string_picker(self, line):
        """STRING_PICK <source> <positions> INTO <target>"""
        m = re.match(r'^STRING_PICK\s+(\w+)\s+"([^"]+)"\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid: {line}")
        return Modifier(name=f"Pick from {m.group(1)}", modifier_type="StringPickerModifier",
                       properties=[
                           Property(name="SourceString", type="value", data_definition_name=m.group(1)),
                           Property(name="Positions", type="value", constant_value=m.group(2), constant_data_type=DataType.String),
                           Property(name="TargetString", type="value", data_definition_name=m.group(3)),
                       ])

    def _parse_string_to_map(self, line):
        """STRING_TO_MAP <source> field="<fd>" value="<vd>" INTO <target>"""
        m = re.match(r'^STRING_TO_MAP\s+(\w+)\s+field="([^"]+)"\s+value="([^"]+)"\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid: {line}")
        return Modifier(name=f"String to map {m.group(1)}", modifier_type="StringToMapModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="FieldDelimiter", type="value", constant_value=m.group(2), constant_data_type=DataType.String),
                           Property(name="ValueDelimiter", type="value", constant_value=m.group(3), constant_data_type=DataType.String),
                           Property(name="Target", type="value", data_definition_name=m.group(4)),
                       ])

    def _parse_create_address(self, line):
        """CREATE_ADDRESS <source> <category> INTO <target>"""
        m = re.match(r'^CREATE_ADDRESS\s+(\w+)\s+(\w+)\s+INTO\s+(\w+)$', line, re.IGNORECASE)
        if not m:
            raise DSLParseError(f"Invalid: {line}")
        return Modifier(name=f"Create address from {m.group(1)}", modifier_type="CreateAddressStringModifier",
                       properties=[
                           Property(name="Source", type="value", data_definition_name=m.group(1)),
                           Property(name="Category", type="value", data_definition_name=m.group(2)),
                           Property(name="Target", type="value", data_definition_name=m.group(3)),
                       ])

    def _parse_multi_lookup_set(self, line):
        """MULTI_LOOKUP_SET table="..." columns="..." keys=<p> results="..." targets=<t> [search=<type>]"""
        attrs = dict(re.findall(r'(\w+)\s*=\s*"([^"]+)"', line))
        for m_iter in re.finditer(r'(\w+)\s*=\s*([^\s"]+)', line):
            if m_iter.group(1) not in attrs and m_iter.group(1) != "MULTI_LOOKUP_SET":
                attrs[m_iter.group(1)] = m_iter.group(2)
        props = [
            Property(name="Table", type="value", constant_value=attrs.get("table", ""), constant_data_type=DataType.String),
            Property(name="ColumnsToSearch", type="value", constant_value=attrs.get("columns", ""), constant_data_type=DataType.String),
            Property(name="Keys", type="value", constant_value=attrs.get("keys", ""), constant_data_type=DataType.String),
            Property(name="ColumnsToReturn", type="value", constant_value=attrs.get("results", ""), constant_data_type=DataType.String),
            Property(name="Targets", type="value", constant_value=attrs.get("targets", ""), constant_data_type=DataType.String),
            Property(name="SearchType", type="", constant_value=attrs.get("search", "EXACT_MATCH")),
        ]
        return Modifier(name="Multi-column lookup", modifier_type="GlobalTableMultipleColumnQueryModifier", properties=props)

    # --- Helpers ---

    def _parse_value_expression(self, value, func):
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return Property(name="", type="value", constant_value=value[1:-1], constant_data_type=DataType.String)
        try:
            int(value)
            return Property(name="", type="value", constant_value=value, constant_data_type=None)
        except ValueError:
            pass
        param = next((p for p in func.parameters if p.name == value), None)
        if param:
            return Property(name="", type="value", data_definition_name=value)
        return Property(name="", type="value", constant_value=value, constant_data_type=DataType.String)

    def _generate_node_name(self, condition_expr):
        return f"Check {condition_expr}"[:60]
