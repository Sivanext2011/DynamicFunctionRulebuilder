"""CHA Dynamic Function domain object model."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DataType(Enum):
    String = "String"
    IntegerNumber = "IntegerNumber"
    LongNumber = "LongNumber"
    Boolean = "Boolean"
    StringList = "StringList"
    IntegerNumberList = "IntegerNumberList"
    LongNumberList = "LongNumberList"
    Enumerated = "Enumerated"
    OctetString = "OctetString"
    AddressString = "AddressString"
    AddressStringList = "AddressStringList"
    Measurement = "Measurement"
    DateTime = "DateTime"
    OctetStringList = "OctetStringList"


class ParameterTemplate(Enum):
    InputParameter = "InputParameter"
    OutputParameter = "OutputParameter"
    InternalParameter = "InternalParameter"
    FunctionTemp = "FunctionTemp"


class CompareOperator(Enum):
    EQ = "EQ"
    NEQ = "NEQ"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    ENDS_WITH = "Ends_with_ignore_case"
    STARTS_WITH = "Starts_with_ignore_case"
    CONTAINS = "Contains_ignore_case"


@dataclass
class Parameter:
    name: str
    data_type: DataType
    template: ParameterTemplate
    collection_type: Optional[str] = None  # e.g., "List"


@dataclass
class Property:
    name: str
    type: str  # "value" or ""
    data_definition_name: Optional[str] = None
    data_definition_keys: Optional[list[str]] = None  # indexed access e.g. ["0"], ["1"]
    constant_value: Optional[str] = None
    constant_data_type: Optional[DataType] = None


@dataclass
class Condition:
    name: str
    condition_type: str
    properties: list[Property] = field(default_factory=list)


@dataclass
class Modifier:
    name: str
    modifier_type: str
    properties: list[Property] = field(default_factory=list)


@dataclass
class RuleElement:
    """Base marker for ordered elements within a Node (children or modifiers)."""
    pass


@dataclass
class Node:
    name: str
    condition: Optional[Condition] = None
    children: list[Node] = field(default_factory=list)
    modifiers: list[Modifier] = field(default_factory=list)
    # Ordered sequence preserving original XML element order
    elements: list = field(default_factory=list)  # list of Node | Modifier in order


@dataclass
class DynamicFunction:
    name: str
    description: str = ""
    version_description: str = ""
    parameters: list[Parameter] = field(default_factory=list)
    root_node: Optional[Node] = None

    @property
    def inputs(self) -> list[Parameter]:
        return [p for p in self.parameters if p.template == ParameterTemplate.InputParameter]

    @property
    def outputs(self) -> list[Parameter]:
        return [p for p in self.parameters if p.template == ParameterTemplate.OutputParameter]

    @property
    def internals(self) -> list[Parameter]:
        return [p for p in self.parameters
                if p.template in (ParameterTemplate.InternalParameter, ParameterTemplate.FunctionTemp)]
