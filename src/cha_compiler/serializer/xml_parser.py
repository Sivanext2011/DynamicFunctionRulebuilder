"""XML Parser: Converts CHA RuleConfiguration XML into DynamicFunction object model."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from ..models import (
    DataType, ParameterTemplate,
    Parameter, Property, Condition, Modifier, Node, DynamicFunction,
)


class XmlParser:
    """Parses CHA RuleConfiguration XML into a DynamicFunction object model."""

    def parse(self, xml_text: str) -> DynamicFunction:
        root = ET.fromstring(xml_text)
        spec_el = root.find("DynamicFunctionSpecification")
        rule_el = root.find("Rule")

        func = DynamicFunction(name=spec_el.get("name"))
        func.description = (spec_el.findtext("Description") or "").strip()
        func.version_description = (spec_el.findtext("VersionDescription") or "").strip()

        # Parse parameters from spec
        for inp in spec_el.findall("InputParameter"):
            func.parameters.append(Parameter(
                name=inp.get("name"),
                data_type=DataType(inp.get("type")),
                template=ParameterTemplate.InputParameter,
                collection_type=inp.get("collectionType"),
            ))
        for out in spec_el.findall("OutputParameter"):
            func.parameters.append(Parameter(
                name=out.get("name"),
                data_type=DataType(out.get("type")),
                template=ParameterTemplate.OutputParameter,
                collection_type=out.get("collectionType"),
            ))

        # Parse all params from DataDefinitions (includes FunctionTemp/Internal)
        if rule_el is not None:
            defs_el = rule_el.find("DataDefinitions")
            if defs_el is not None:
                spec_names = {p.name for p in func.parameters}
                for dd in defs_el.findall("DataDefinition"):
                    tmpl_str = dd.get("template")
                    name = dd.get("name")
                    if name in spec_names:
                        # Update collection_type if present
                        ct = dd.get("collectionType")
                        if ct:
                            for p in func.parameters:
                                if p.name == name:
                                    p.collection_type = ct
                        continue
                    try:
                        tmpl = ParameterTemplate(tmpl_str)
                    except ValueError:
                        tmpl = ParameterTemplate.FunctionTemp
                    func.parameters.append(Parameter(
                        name=name,
                        data_type=DataType(dd.get("dataType")),
                        template=tmpl,
                        collection_type=dd.get("collectionType"),
                    ))

            # Parse rule tree
            node_el = rule_el.find("Node")
            if node_el is not None:
                func.root_node = self._parse_node(node_el)

        return func

    def _parse_node(self, el: ET.Element) -> Node:
        node = Node(name=el.get("name", ""))

        cond_el = el.find("Condition")
        if cond_el is not None:
            node.condition = self._parse_condition(cond_el)

        # Parse children in order (preserving Node/Modifier/IteratorNode interleaving)
        for child_el in el:
            if child_el.tag == "Node":
                child_node = self._parse_node(child_el)
                node.children.append(child_node)
                node.elements.append(child_node)
            elif child_el.tag == "IteratorNode":
                iter_node = self._parse_iterator_node(child_el)
                node.children.append(iter_node)
                node.elements.append(iter_node)
            elif child_el.tag == "Modifier":
                mod = self._parse_modifier(child_el)
                node.modifiers.append(mod)
                node.elements.append(mod)

        return node

    def _parse_iterator_node(self, el: ET.Element) -> Node:
        """Parse an IteratorNode into a Node with is_iterator=True marker."""
        node = Node(name=el.get("name", ""))
        # Store iterator properties as a special condition marker
        props = []
        for prop_el in el.findall("Property"):
            props.append(self._parse_property(prop_el))

        # Use a special condition to mark this as an IteratorNode
        node.condition = Condition(
            name=node.name,
            condition_type="IteratorNode",
            properties=props,
        )

        # Parse child elements inside the iterator
        cond_el = el.find("Condition")
        inner_cond = None
        if cond_el is not None:
            inner_cond = self._parse_condition(cond_el)

        for child_el in el:
            if child_el.tag == "Node":
                child_node = self._parse_node(child_el)
                node.children.append(child_node)
                node.elements.append(child_node)
            elif child_el.tag == "Modifier":
                mod = self._parse_modifier(child_el)
                node.modifiers.append(mod)
                node.elements.append(mod)
            elif child_el.tag == "Condition":
                # Store inner condition as first child node
                pass  # handled below

        # If there's a condition inside the iterator, wrap children under it
        if inner_cond:
            cond_node = Node(name=inner_cond.name, condition=inner_cond)
            # Move existing modifiers under the condition node
            cond_node.modifiers = node.modifiers
            cond_node.elements = node.elements
            cond_node.children = node.children
            node.children = [cond_node]
            node.modifiers = []
            node.elements = [cond_node]

        return node

    def _parse_condition(self, el: ET.Element) -> Condition:
        cond = Condition(name=el.get("name", ""), condition_type=el.get("type", ""))
        for prop_el in el.findall("Property"):
            cond.properties.append(self._parse_property(prop_el))
        return cond

    def _parse_modifier(self, el: ET.Element) -> Modifier:
        mod = Modifier(name=el.get("name", ""), modifier_type=el.get("type", ""))
        for prop_el in el.findall("Property"):
            mod.properties.append(self._parse_property(prop_el))
        return mod

    def _parse_property(self, el: ET.Element) -> Property:
        prop = Property(name=el.get("name", ""), type=el.get("type", ""))

        dd_el = el.find("DataDefinition")
        if dd_el is not None:
            prop.data_definition_name = dd_el.get("name")
            # Check for indexed keys
            keys_el = dd_el.find("Keys")
            if keys_el is not None:
                keys = []
                for const_el in keys_el.findall("Constant"):
                    keys.append(const_el.text or "")
                if keys:
                    prop.data_definition_keys = keys
        else:
            const_el = el.find("Constant")
            if const_el is not None:
                prop.constant_value = const_el.text or ""
                dt = const_el.get("dataType")
                if dt:
                    try:
                        prop.constant_data_type = DataType(dt)
                    except ValueError:
                        pass
            elif el.text and el.text.strip():
                prop.constant_value = el.text.strip()

        return prop
