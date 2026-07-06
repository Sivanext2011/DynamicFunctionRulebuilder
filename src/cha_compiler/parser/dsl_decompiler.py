"""DSL Decompiler: Converts DynamicFunction object model back to DSL text."""
from __future__ import annotations
from ..models import (
    ParameterTemplate, Property, Condition, Modifier, Node, DynamicFunction,
)
from ..models.dynamic_function import DataType


class DSLDecompiler:
    """Converts a DynamicFunction object model to CHA DSL text."""

    def decompile(self, func: DynamicFunction) -> str:
        lines: list[str] = []
        lines.append(f"FUNCTION {func.name}")
        lines.append("")

        if func.inputs:
            lines.append("INPUT")
            for p in func.inputs:
                ct = f" [{p.collection_type}]" if p.collection_type else ""
                lines.append(f"    {p.name} : {p.data_type.value}{ct}")
            lines.append("")

        if func.outputs:
            lines.append("OUTPUT")
            for p in func.outputs:
                ct = f" [{p.collection_type}]" if p.collection_type else ""
                lines.append(f"    {p.name} : {p.data_type.value}{ct}")
            lines.append("")

        if func.internals:
            lines.append("INTERNAL")
            for p in func.internals:
                ct = f" [{p.collection_type}]" if p.collection_type else ""
                lines.append(f"    {p.name} : {p.data_type.value}{ct}")
            lines.append("")

        lines.append("RULE")
        lines.append("")

        if func.root_node:
            self._decompile_node_children(func.root_node, lines, indent=0)

        return "\n".join(lines).rstrip() + "\n"

    def _decompile_node_children(self, node: Node, lines: list[str], indent: int):
        if node.elements:
            for elem in node.elements:
                if isinstance(elem, Node):
                    self._decompile_node(elem, lines, indent)
                elif isinstance(elem, Modifier):
                    self._decompile_modifier(elem, lines, indent)
        else:
            for child in node.children:
                self._decompile_node(child, lines, indent)
            for mod in node.modifiers:
                self._decompile_modifier(mod, lines, indent)

    def _decompile_node(self, node: Node, lines: list[str], indent: int):
        prefix = "    " * indent

        if node.condition:
            if node.condition.condition_type == "IteratorNode":
                # Special handling for IteratorNode
                coll = self._get_prop(node.condition.properties, "Collection")
                val = self._get_prop(node.condition.properties, "IterationValue")
                idx = self._get_prop(node.condition.properties, "IterationIndex")
                c = coll.data_definition_name if coll else "?"
                v = val.data_definition_name if val else "item"
                i = idx.data_definition_name if idx else "i"
                lines.append(f"{prefix}ITERATE {c} AS {v} INDEX {i}")
                self._decompile_node_body(node, lines, indent + 1)
                lines.append("")
            else:
                cond_str = self._condition_to_dsl(node.condition)
                lines.append(f"{prefix}IF {cond_str}")
                self._decompile_node_body(node, lines, indent + 1)
                lines.append("")
        elif node.name == "Else":
            lines.append(f"{prefix}ELSE")
            self._decompile_node_body(node, lines, indent + 1)
            lines.append("")
        else:
            self._decompile_node_body(node, lines, indent)

    def _decompile_node_body(self, node: Node, lines: list[str], indent: int):
        if node.elements:
            for elem in node.elements:
                if isinstance(elem, Node):
                    self._decompile_node(elem, lines, indent)
                elif isinstance(elem, Modifier):
                    self._decompile_modifier(elem, lines, indent)
        else:
            for child in node.children:
                self._decompile_node(child, lines, indent)
            for mod in node.modifiers:
                self._decompile_modifier(mod, lines, indent)

    # --- Condition decompilation ---

    def _condition_to_dsl(self, cond: Condition) -> str:
        if cond.condition_type == "DoesDataExistCondition":
            data_prop = self._get_prop(cond.properties, "Data")
            if data_prop and data_prop.data_definition_name:
                return f"EXISTS {data_prop.data_definition_name}"

        if cond.condition_type == "CompareDataCondition":
            source = self._get_prop(cond.properties, "SourceDataComparable")
            operator = self._get_prop(cond.properties, "Operator")
            compare_to = self._get_prop(cond.properties, "SourceDataCompareTo")
            if source and operator and compare_to:
                var_name = source.data_definition_name or "?"
                op_map = {"EQ": "==", "NEQ": "!=", "GT": ">", "GTE": ">=", "LT": "<", "LTE": "<="}
                op_str = op_map.get(operator.constant_value, "==")
                value = self._value_to_dsl(compare_to)
                return f"{var_name} {op_str} {value}"

        if cond.condition_type == "BooleanCondition":
            data_prop = self._get_prop(cond.properties, "Data")
            negate = self._get_prop(cond.properties, "Negate")
            if data_prop:
                name = data_prop.data_definition_name or "?"
                if negate and negate.constant_value == "true":
                    return f"NOT {name}"
                return name

        if cond.condition_type == "LengthCondition":
            data_prop = self._get_prop(cond.properties, "Data")
            operator = self._get_prop(cond.properties, "Operator")
            compare = self._get_prop(cond.properties, "CompareValue")
            if data_prop and operator and compare:
                var = data_prop.data_definition_name or "?"
                op_map = {"EQ": "==", "NEQ": "!=", "GT": ">", "GTE": ">=", "LT": "<", "LTE": "<="}
                op_str = op_map.get(operator.constant_value, "==")
                val = compare.constant_value or "?"
                return f"LENGTH {var} {op_str} {val}"

        if cond.condition_type == "GlobalTableQueryCondition":
            table_prop = self._get_prop(cond.properties, "Table")
            col_prop = self._get_prop(cond.properties, "ColumnToSearch")
            key_prop = self._get_prop(cond.properties, "Key")
            search_prop = self._get_prop(cond.properties, "SearchType")
            table = table_prop.constant_value if table_prop else "?"
            column = col_prop.constant_value if col_prop else "?"
            key = key_prop.data_definition_name if key_prop else "?"
            search = search_prop.constant_value if search_prop else "EXACT_MATCH"
            return f'LOOKUP table="{table}" column="{column}" key={key} search={search}'

        return cond.name

    # --- Modifier decompilation ---

    def _decompile_modifier(self, mod: Modifier, lines: list[str], indent: int):
        prefix = "    " * indent
        mt = mod.modifier_type

        if mt == "ExitModifier":
            lines.append(f"{prefix}EXIT")
        elif mt == "BreakIterationModifier":
            lines.append(f"{prefix}BREAK")
        elif mt == "SetDataModifier":
            source = self._get_prop(mod.properties, "Source")
            target = self._get_prop(mod.properties, "Target")
            if source and target:
                lines.append(f"{prefix}SET {target.data_definition_name or '?'} = {self._value_to_dsl(source)}")
            else:
                lines.append(f"{prefix}# SetDataModifier: {mod.name}")
        elif mt == "ConvertDataTypeModifier":
            source = self._get_prop(mod.properties, "Source")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}CONVERT {s} TO {t}")
        elif mt == "SplitStringModifier":
            source = self._get_prop(mod.properties, "Source")
            delim = self._get_prop(mod.properties, "Delimiter")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            d = delim.constant_value if delim else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f'{prefix}SPLIT {s} BY "{d}" INTO {t}')
        elif mt == "SubstringModifier":
            source = self._get_prop(mod.properties, "SourceString")
            start = self._get_prop(mod.properties, "StartIndex")
            end = self._get_prop(mod.properties, "EndIndex")
            target = self._get_prop(mod.properties, "TargetString")
            s = source.data_definition_name if source else "?"
            if source and source.data_definition_keys:
                s += f"[{source.data_definition_keys[0]}]"
            st = start.constant_value if start else "0"
            en = end.constant_value if end else "0"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}SUBSTRING {s} {st} {en} INTO {t}")
        elif mt == "ReplaceStringModifier":
            source = self._get_prop(mod.properties, "Source")
            regex = self._get_prop(mod.properties, "Regex")
            repl = self._get_prop(mod.properties, "Replace")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            r = regex.constant_value if regex else "?"
            rp = repl.constant_value if repl else ""
            t = target.data_definition_name if target else "?"
            lines.append(f'{prefix}REPLACE {s} "{r}" WITH "{rp}" INTO {t}')
        elif mt == "LengthModifier":
            source = self._get_prop(mod.properties, "Source")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}LENGTH {s} INTO {t}")
        elif mt == "BasicMathModifier":
            left = self._get_prop(mod.properties, "LeftOperand")
            op = self._get_prop(mod.properties, "Operator")
            right = self._get_prop(mod.properties, "RightOperand")
            target = self._get_prop(mod.properties, "Target")
            op_map = {"ADD": "+", "SUBTRACT": "-", "MULTIPLY": "*", "DIVIDE": "/"}
            l = left.data_definition_name if left else "?"
            r = right.data_definition_name if right else "?"
            o = op_map.get(op.constant_value, "+") if op else "+"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}MATH {t} = {l} {o} {r}")
        elif mt == "AddStringModifier":
            s1 = self._get_prop(mod.properties, "SourceString") or self._get_prop(mod.properties, "Source1") or self._get_prop(mod.properties, "Source")
            s2 = self._get_prop(mod.properties, "AddString") or self._get_prop(mod.properties, "Source2")
            target = self._get_prop(mod.properties, "TargetString") or self._get_prop(mod.properties, "Target")
            a = self._value_to_dsl(s1) if s1 else "?"
            b = self._value_to_dsl(s2) if s2 else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}CONCAT {a}, {b} INTO {t}")
        elif mt == "EnumerationModifier":
            source = self._get_prop(mod.properties, "Source")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}ENUMERATE {s} INTO {t}")
        elif mt == "GlobalTableQueryModifier":
            table = self._get_prop(mod.properties, "Table")
            col = self._get_prop(mod.properties, "ColumnToSearch")
            key = self._get_prop(mod.properties, "Key")
            result = self._get_prop(mod.properties, "ColumnToReturn")
            target = self._get_prop(mod.properties, "Target")
            search = self._get_prop(mod.properties, "SearchType")
            default = self._get_prop(mod.properties, "DefaultValue")
            parts = [f'LOOKUP_SET table="{table.constant_value if table else "?"}"']
            parts.append(f'column="{col.constant_value if col else "?"}"')
            parts.append(f'key={key.data_definition_name if key else "?"}')
            parts.append(f'result="{result.constant_value if result else "?"}"')
            parts.append(f'target={target.data_definition_name if target else "?"}')
            parts.append(f'search={search.constant_value if search else "EXACT_MATCH"}')
            if default and default.constant_value:
                parts.append(f'default="{default.constant_value}"')
            lines.append(f"{prefix}{' '.join(parts)}")
        elif mt == "OctetHexConvertModifier":
            source = self._get_prop(mod.properties, "Source")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}OCTET_TO_HEX {s} INTO {t}")
        elif mt == "IpAddressToStringModifier":
            source = self._get_prop(mod.properties, "Source")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}IP_TO_STRING {s} INTO {t}")
        elif mt == "TbcdToStringModifier":
            source = self._get_prop(mod.properties, "Source")
            fmt = self._get_prop(mod.properties, "Format")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            f = fmt.constant_value if fmt else "TBCD"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}TBCD_TO_STRING {s} {f} INTO {t}")
        elif mt == "ExtractBitsModifier":
            source = self._get_prop(mod.properties, "Source")
            byte_idx = self._get_prop(mod.properties, "ByteIndex")
            bit_off = self._get_prop(mod.properties, "BitOffset")
            bit_len = self._get_prop(mod.properties, "BitLength")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            bi = byte_idx.constant_value if byte_idx else "0"
            bo = bit_off.constant_value if bit_off else "0"
            bl = bit_len.constant_value if bit_len else "0"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}EXTRACT_BITS {s} {bi} {bo} {bl} INTO {t}")
        elif mt == "ExtractOctetModifier":
            source = self._get_prop(mod.properties, "Source")
            start = self._get_prop(mod.properties, "StartIndex")
            length = self._get_prop(mod.properties, "LengthToRead")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            st = start.constant_value if start else "0"
            ln = length.constant_value if length else "0"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}EXTRACT_OCTET {s} {st} {ln} INTO {t}")
        elif mt == "ExtractNtetModifier":
            source = self._get_prop(mod.properties, "Source")
            nbit = self._get_prop(mod.properties, "Nbit")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            n = nbit.constant_value if nbit else "0"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}EXTRACT_NTET {s} {n} INTO {t}")
        elif mt == "BitMaskModifier":
            source = self._get_prop(mod.properties, "Source")
            mask = self._get_prop(mod.properties, "Mask")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            m_val = mask.constant_value if mask else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}BITMASK {s} {m_val} INTO {t}")
        elif mt == "StringPickerModifier":
            source = self._get_prop(mod.properties, "SourceString")
            positions = self._get_prop(mod.properties, "Positions")
            target = self._get_prop(mod.properties, "TargetString")
            s = source.data_definition_name if source else "?"
            p = positions.constant_value if positions else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f'{prefix}STRING_PICK {s} "{p}" INTO {t}')
        elif mt == "StringToMapModifier":
            source = self._get_prop(mod.properties, "Source")
            fd = self._get_prop(mod.properties, "FieldDelimiter")
            vd = self._get_prop(mod.properties, "ValueDelimiter")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            f = fd.constant_value if fd else "?"
            v = vd.constant_value if vd else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f'{prefix}STRING_TO_MAP {s} field="{f}" value="{v}" INTO {t}')
        elif mt == "CreateAddressStringModifier":
            source = self._get_prop(mod.properties, "Source")
            cat = self._get_prop(mod.properties, "Category")
            target = self._get_prop(mod.properties, "Target")
            s = source.data_definition_name if source else "?"
            c = cat.data_definition_name if cat else "?"
            t = target.data_definition_name if target else "?"
            lines.append(f"{prefix}CREATE_ADDRESS {s} {c} INTO {t}")
        elif mt == "GlobalTableMultipleColumnQueryModifier":
            table = self._get_prop(mod.properties, "Table")
            cols = self._get_prop(mod.properties, "ColumnsToSearch")
            keys = self._get_prop(mod.properties, "Keys")
            results = self._get_prop(mod.properties, "ColumnsToReturn")
            targets = self._get_prop(mod.properties, "Targets")
            search = self._get_prop(mod.properties, "SearchType")
            parts = [f'MULTI_LOOKUP_SET table="{table.constant_value if table else "?"}"']
            parts.append(f'columns="{cols.constant_value if cols else "?"}"')
            parts.append(f'keys={keys.constant_value if keys else "?"}')
            parts.append(f'results="{results.constant_value if results else "?"}"')
            parts.append(f'targets={targets.constant_value if targets else "?"}')
            parts.append(f'search={search.constant_value if search else "EXACT_MATCH"}')
            lines.append(f"{prefix}{' '.join(parts)}")
        else:
            # Truly unsupported modifier
            lines.append(f"{prefix}# {mt}: {mod.name}")

    # --- Helpers ---

    def _get_prop(self, properties: list[Property], name: str):
        return next((p for p in properties if p.name == name), None)

    def _value_to_dsl(self, prop: Property) -> str:
        if prop.data_definition_name:
            if prop.data_definition_keys:
                return f"{prop.data_definition_name}[{prop.data_definition_keys[0]}]"
            return prop.data_definition_name
        if prop.constant_value is not None:
            if prop.constant_data_type == DataType.String:
                return f'"{prop.constant_value}"'
            return prop.constant_value
        return "?"
