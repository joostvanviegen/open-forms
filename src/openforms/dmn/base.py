from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

from openforms.plugins.plugin import AbstractBasePlugin


@dataclass
class DecisionDefinition:
    """
    Represent a single decision definition.
    """

    identifier: str
    label: str


@dataclass
class DecisionDefinitionVersion:
    """
    Represent a version of a decision definition.
    """

    id: str
    label: str


class BasePlugin(ABC, AbstractBasePlugin):
    @abstractmethod
    def get_available_decision_definitions(self) -> List[DecisionDefinition]:
        """
        Get a collection of all the available decision definitions.

        The end-user configuring the evaluation selects one of the available choices.
        Note that different versions of the same definition must be filtered out, as
        specifying a particular version is a separate action.
        """
        raise NotImplementedError()  # pragma: nocover

    @abstractmethod
    def evaluate(
        self, definition_id: str, *, version: str = "", input_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate the decision definition with the given input data.
        """
        raise NotImplementedError()  # pragma: nocover

    def get_decision_definition_versions(
        self, definition_id: str
    ) -> List[DecisionDefinitionVersion]:
        """
        Get a collection of available versions for a given decision definition.

        Backends supporting versioning can implement this method to offer more
        granularity. By default we assume versioning is not supported and return an
        empty list.
        """
        return []

    def get_definition_xml(self, definition_id: str, version: str = "") -> str:
        """
        Return the standards-compliant XML definition of the decision table.

        If this is not available, return an empty string.
        """
        return ""
