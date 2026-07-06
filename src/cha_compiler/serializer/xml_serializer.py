"""XML Serializer: Converts DynamicFunction object model to CHA-compatible XML."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from xml.dom import minidom
from ..models import (
    DataType, ParameterTemplate,
    Parameter, Property, Condition, Modifier, Node, DynamicFunction,
)


class XmlSerializer:
    """Serializes a DynamicFunction to CHA RuleConfiguration XML."""

    def serialize(self, func: DynamicFunction) -> str:
        root = ET.Element("RuleConfiguration")
        self._build_specification(root, func)
        self._build_rule(root, func)
        return self._to_pretty_xml(root)

    def _build_specification(self, root: ET.Element, func: DynamicFunction):
        spec = ET.SubElement(root, "DynamicFunctionSpecification", name=func.name)
        desc = ET.SubElement(spec, "Description")
        desc.text = func.description
        ver_desc = ET.SubElement(spec, "VersionDescription")
        ver_desc.text = func.version_description or None

        for p in func.inputs:
            attrs = {"name": p.name, "type": p.data_type.value}
            if p.collection_type:
                attrs["collectionType"] = p.collection_type
            ET.SubElement(spec, "InputParameter", **attrs)
        for p in func.outputs:
            attrs = {"name": p.name, "type": p.data_type.value}
            if p.collection_type:
                attrs["collectionType"] = p.collection_type
            ET.SubElement(spec, "OutputParameter", **attrs)

    def _build_rule(self, root: ET.Element, func: DynamicFunction):
        rule_el = ET.SubElement(root, "Rule")
        self._build_data_definitions(rule_el, func)
        if func.root_node:
            self._build_node(rule_el, func.root_node, func)

    def _build_data_definitions(self, rule_el: ET.Element, func: DynamicFunction):
        defs_el = ET.SubElement(rule_el, "DataDefinitions")
        for p in func.parameters:
            attrs = {"dataType": p.data_type.value, "name": p.name, "template": p.template.value}
            if p.collection_type:
                attrs["collectionType"] = p.collection_type
            dd = ET.SubElement(defs_el, "DataDefinition", **attrs)
            keys = ET.SubElement(dd, "Keys")
            const = ET.SubElement(keys, "Constant", dataType="String")
            const.text = p.name

    def _build_node(self, parent_el: ET.Element, node: Node, func: DynamicFunction):
        node_el = ET.SubElement(parent_el, "Node", name=node.name)

        if node.condition:
            self._build_condition(node_el, node.condition, func)

        # Use ordered elements if available, otherwise fallback to children+modifiers
        if node.elements:
            for elem in node.elements:
                if isinstance(elem, Node):
                    self._build_node(node_el, elem, func)
                elif isinstance(elem, Modifier):
                    self._build_modifier(node_el, elem, func)
        else:
            for child in node.children:
                self._build_node(node_el, child, func)
            for modifier in node.modifiers:
                self._build_modifier(node_el, modifier, func)

    def _build_condition(self, node_el: ET.Element, cond: Condition, func: DynamicFunction):
        cond_el = ET.SubElement(node_el, "Condition", name=cond.name, type=cond.condition_type)
        for prop in cond.properties:
            self._build_property(cond_el, prop, func)

    def _build_modifier(self, node_el: ET.Element, mod: Modifier, func: DynamicFunction):
        mod_el = ET.SubElement(node_el, "Modifier", name=mod.name, type=mod.modifier_type)
        for prop in mod.properties:
            self._build_property(mod_el, prop, func)

    def _build_property(self, parent_el: ET.Element, prop: Property, func: DynamicFunction):
        attrs = {"name": prop.name}
        if prop.type:
            attrs["type"] = prop.type
        prop_el = ET.SubElement(parent_el, "Property", **attrs)

        if prop.data_definition_name:
            dd_el = ET.SubElement(prop_el, "DataDefinition", name=prop.data_definition_name)
            if prop.data_definition_keys:
                keys_el = ET.SubElement(dd_el, "Keys")
                for key in prop.data_definition_keys:
                    const_el = ET.SubElement(keys_el, "Constant", dataType="String")
                    const_el.text = key
        elif prop.constant_value is not None:
            if prop.constant_data_type:
                const_el = ET.SubElement(prop_el, "Constant", dataType=prop.constant_data_type.value)
                const_el.text = prop.constant_value if prop.constant_value else None
            elif not prop.type:
                # Inline text property (like Operator, SearchType)
                prop_el.text = prop.constant_value
            else:
                data_type = self._resolve_constant_type(prop, func)
                const_el = ET.SubElement(prop_el, "Constant", dataType=data_type.value)
                const_el.text = prop.constant_value if prop.constant_value else None

    def _resolve_constant_type(self, prop: Property, func: DynamicFunction) -> DataType:
        if prop.constant_data_type:
            return prop.constant_data_type
        try:
            int(prop.constant_value)
            return DataType.IntegerNumber
        except (ValueError, TypeError):
            return DataType.String

    def _to_pretty_xml(self, root: ET.Element) -> str:
        rough = ET.tostring(root, encoding="unicode", xml_declaration=False)
        dom = minidom.parseString(rough)
        pretty = dom.toprettyxml(indent="    ", encoding=None)
        lines = [l for l in pretty.splitlines() if l.strip()]
        lines[0] = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        return "\n".join(lines) + "\n"
