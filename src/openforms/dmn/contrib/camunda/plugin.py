import json
import logging
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

import requests
import simplejson  # dependency pulled in via mail-parser...
from django_camunda.client import Camunda, get_client
from django_camunda.dmn import evaluate_dmn

from ...base import BasePlugin, DecisionDefinition, DecisionDefinitionVersion
from ...registry import register
from .checks import check_config

logger = logging.getLogger(__name__)


def _get_decision_definition_id(client: Camunda, key: str, version: str = ""):
    query = {"key": key}
    # handle version pinning
    if version:
        query["version"] = version
    else:
        query["latestVersion"] = "true"

    # get the results to figure out the decision definition ID
    results = client.get("decision-definition", query)
    num_results = len(results)

    if not results or num_results > 1:  # pragma: nocover
        logger.warning(
            "None or multiple decision-definition found in the API, found %d results for query %r.",
            num_results,
            query,
        )
        return ""

    return results[0]["id"]


def handle_camunda_error(error: requests.HTTPError):
    logger.exception("Error occurred while calling Camunda API", exc_info=error)
    if error.response is None:
        raise

    try:
        response_body = error.response.json()
    except (json.JSONDecodeError, simplejson.JSONDecodeError):
        logger.exception("Could not decode JSON data in error response body")
    else:
        logger.error("Camunda error information: %r", response_body)


@register("camunda7")
class Plugin(BasePlugin):
    verbose_name = _("Camunda")

    @staticmethod
    def get_available_decision_definitions() -> List[DecisionDefinition]:
        with get_client() as client:
            results = client.get(
                "decision-definition",
                params={"latestVersion": "true"},
            )
        return [
            DecisionDefinition(
                identifier=result["key"], label=result["name"] or result["key"]
            )
            for result in results
        ]

    @staticmethod
    def evaluate(
        definition_id: str, *, version: str = "", input_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        with get_client() as client:
            camunda_id = _get_decision_definition_id(client, definition_id, version)
            try:
                result = evaluate_dmn(
                    dmn_key=definition_id,
                    dmn_id=camunda_id,
                    input_values=input_values,
                    client=client,
                )
            except requests.HTTPError as error:
                handle_camunda_error(error)
                return {}
        return result

    @staticmethod
    def get_decision_definition_versions(
        definition_id: str,
    ) -> List[DecisionDefinitionVersion]:
        """
        Get a collection of available versions for a given decision definition.

        :param definition_id: the key of the decision definition in the Camunda API.
        """
        with get_client() as client:
            results = client.get(
                "decision-definition",
                params={"key": definition_id, "sortBy": "version", "sortOrder": "desc"},
            )
        return [
            DecisionDefinitionVersion(
                id=str(result["version"]),
                label=_("v{version} (version tag: {version_tag})").format(
                    version=result["version"],
                    version_tag=result["version_tag"] or _("n/a"),
                ),
            )
            for result in results
        ]

    @staticmethod
    def get_definition_xml(definition_id: str, version: str = "") -> str:
        with get_client() as client:
            camunda_id = _get_decision_definition_id(client, definition_id, version)
            xml_response = client.get(f"decision-definition/{camunda_id}/xml")
        return xml_response["dmn_xml"]

    def check_config(self):
        check_config(self)
