"""Validation layer for DynamicFunction objects."""
from __future__ import annotations
from dataclasses import dataclass
from .models import DynamicFunction, Node, Modifier, ParameterTemplate


@dataclass
class ValidationError:
    message: str
    severity: str = "ERROR"


@dataclass
class ValidationWarning:
    message: str
    severity: str = "WARNING"


class Validator:
    """Validates a DynamicFunction before package generation."""

    def validate(self, func: DynamicFunction) -> list[ValidationError]:
        errors: list[ValidationError] = []

        if not func.name:
            errors.append(ValidationError("Function name is required"))

        if not func.inputs:
            errors.append(ValidationError("At least one input parameter is required"))

        if not func.outputs:
            errors.append(ValidationError("At least one output parameter is required"))

        if not func.root_node:
            errors.append(ValidationError("Rule must contain at least one node"))

        # Duplicate parameter names
        names = [p.name for p in func.parameters]
        dupes = set(n for n in names if names.count(n) > 1)
        for d in dupes:
            errors.append(ValidationError(f"Duplicate parameter name: {d}"))

        # Validate references
        if func.root_node:
            param_names = set(names)
            self._validate_node_refs(func.root_node, param_names, errors)

        return errors

    def validate_warnings(self, func: DynamicFunction) -> list[ValidationWarning]:
        """Additional non-fatal warnings for best practice."""
        warnings: list[ValidationWarning] = []
        if not func.root_node:
            return warnings

        param_names = set(p.name for p in func.parameters)

        # Check for unused internal parameters
        used_params = set()
        self._collect_used_params(func.root_node, used_params)
        for p in func.internals:
            if p.name not in used_params:
                warnings.append(ValidationWarning(f"Internal parameter '{p.name}' is declared but never used"))

        # Check for output parameters never SET
        set_targets = set()
        self._collect_set_targets(func.root_node, set_targets)
        for p in func.outputs:
            if p.name not in set_targets:
                warnings.append(ValidationWarning(f"Output parameter '{p.name}' is never assigned a value"))

        # Check COBA table URIs
        self._check_coba_uris(func.root_node, warnings)

        # Check SUBSTRING bounds
        self._check_substring_bounds(func.root_node, warnings)

        return warnings

    def _validate_node_refs(self, node: Node, param_names: set[str], errors: list[ValidationError]):
        if node.condition:
            for prop in node.condition.properties:
                if prop.data_definition_name and prop.data_definition_name not in param_names:
                    errors.append(ValidationError(
                        f"Condition '{node.condition.name}' references undefined parameter: {prop.data_definition_name}"
                    ))

        all_mods = node.modifiers
        all_children = node.children
        if node.elements:
            all_mods = [e for e in node.elements if isinstance(e, Modifier)]
            all_children = [e for e in node.elements if isinstance(e, Node)]

        for mod in all_mods:
            for prop in mod.properties:
                if prop.data_definition_name and prop.data_definition_name not in param_names:
                    errors.append(ValidationError(
                        f"Modifier '{mod.name}' references undefined parameter: {prop.data_definition_name}"
                    ))

        for child in all_children:
            self._validate_node_refs(child, param_names, errors)

    def _collect_used_params(self, node: Node, used: set[str]):
        if node.condition:
            for prop in node.condition.properties:
                if prop.data_definition_name:
                    used.add(prop.data_definition_name)
        for mod in node.modifiers:
            for prop in mod.properties:
                if prop.data_definition_name:
                    used.add(prop.data_definition_name)
        for child in node.children:
            self._collect_used_params(child, used)

    def _collect_set_targets(self, node: Node, targets: set[str]):
        all_mods = node.modifiers
        if node.elements:
            all_mods = [e for e in node.elements if isinstance(e, Modifier)]
        for mod in all_mods:
            if mod.modifier_type == "SetDataModifier":
                target = next((p for p in mod.properties if p.name == "Target"), None)
                if target and target.data_definition_name:
                    targets.add(target.data_definition_name)
            elif mod.modifier_type in ("AddStringModifier", "GlobalTableQueryModifier", "SubstringModifier",
                                       "SplitStringModifier", "ConvertDataTypeModifier", "ReplaceStringModifier",
                                       "LengthModifier", "BasicMathModifier", "EnumerationModifier",
                                       "GlobalTableMultipleColumnQueryModifier"):
                target = next((p for p in mod.properties if p.name in ("Target", "TargetString", "Output")), None)
                if target and target.data_definition_name:
                    targets.add(target.data_definition_name)
        all_children = node.children
        if node.elements:
            all_children = [e for e in node.elements if isinstance(e, Node)]
        for child in all_children:
            self._collect_set_targets(child, targets)

    def _check_coba_uris(self, node: Node, warnings: list[ValidationWarning]):
        if node.condition and node.condition.condition_type == "GlobalTableQueryCondition":
            table_prop = next((p for p in node.condition.properties if p.name == "Table"), None)
            if table_prop and table_prop.constant_value:
                uri = table_prop.constant_value
                if not uri.startswith("rmref://coba/globalListSpecification/"):
                    warnings.append(ValidationWarning(
                        f"COBA table URI doesn't match expected format: {uri}"
                    ))

        for mod in node.modifiers:
            if mod.modifier_type in ("GlobalTableQueryModifier", "GlobalTableMultipleColumnQueryModifier"):
                table_prop = next((p for p in mod.properties if p.name == "Table"), None)
                if table_prop and table_prop.constant_value:
                    uri = table_prop.constant_value
                    if not uri.startswith("rmref://coba/globalListSpecification/"):
                        warnings.append(ValidationWarning(
                            f"COBA table URI doesn't match expected format: {uri}"
                        ))

        for child in node.children:
            self._check_coba_uris(child, warnings)

    def _check_substring_bounds(self, node: Node, warnings: list[ValidationWarning]):
        for mod in node.modifiers:
            if mod.modifier_type == "SubstringModifier":
                start = next((p for p in mod.properties if p.name == "StartIndex"), None)
                end = next((p for p in mod.properties if p.name == "EndIndex"), None)
                if start and end and start.constant_value and end.constant_value:
                    try:
                        s, e = int(start.constant_value), int(end.constant_value)
                        if s >= e:
                            warnings.append(ValidationWarning(
                                f"SUBSTRING '{mod.name}': StartIndex ({s}) >= EndIndex ({e})"
                            ))
                        if e > 100:
                            warnings.append(ValidationWarning(
                                f"SUBSTRING '{mod.name}': EndIndex ({e}) is unusually large"
                            ))
                    except ValueError:
                        pass
        for child in node.children:
            self._check_substring_bounds(child, warnings)
