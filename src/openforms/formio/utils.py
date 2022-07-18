import logging
from datetime import date, datetime
from typing import Any, Dict, Iterator, List

from .constants import COMPONENT_DATATYPES
from .typing import Component

logger = logging.getLogger(__name__)


def iter_components(
    configuration: dict, recursive=True, _is_root=True, _mark_root=False
) -> Iterator[Component]:
    components = configuration.get("components")
    if configuration.get("type") == "columns" and recursive:
        assert not components, "Both nested components and columns found"
        for column in configuration["columns"]:
            yield from iter_components(
                configuration=column, recursive=recursive, _is_root=False
            )

    if components:
        for component in components:
            if _mark_root:
                component["_is_root"] = _is_root
            yield component
            if recursive:
                yield from iter_components(
                    configuration=component, recursive=recursive, _is_root=False
                )


def flatten(configuration: dict) -> Dict[str, Any]:
    return {
        component["key"]: component
        for component in iter_components(configuration, recursive=True)
    }


def get_default_values(configuration: dict) -> Dict[str, Any]:
    defaults = {}

    for component in iter_components(configuration, recursive=True):
        if "key" not in component:
            continue
        if "defaultValue" not in component:
            continue
        defaults[component["key"]] = component["defaultValue"]

    return defaults


def is_layout_component(component):
    # Adapted from isLayoutComponent util function in Formio
    # https://github.com/formio/formio.js/blob/4.13.x/src/utils/formUtils.js#L25
    column = component.get("columns")
    components = component.get("components")
    rows = component.get("rows")

    if (
        (column and isinstance(column, list))
        or (components and isinstance(components, list))
        or (rows and isinstance(rows, list))
    ):
        return True

    return False


def format_date_value(date_value: str) -> str:
    try:
        parsed_date = date.fromisoformat(date_value)
    except ValueError:
        try:
            parsed_date = datetime.strptime(date_value, "%Y%m%d").date()
        except ValueError:
            logger.info(
                "Invalid date %s for prefill of date field. Using empty value.",
                date_value,
            )
            return ""

    return parsed_date.isoformat()


def get_component_datatype(component):
    component_type = component["type"]
    return COMPONENT_DATATYPES.get(component_type, "string")


def get_component_default_value(component):
    # Formio has a getter for the:
    # - emptyValue: https://github.com/formio/formio.js/blob/4.13.x/src/components/textfield/TextField.js#L58
    # - defaultValue:
    #    https://github.com/formio/formio.js/blob/4.13.x/src/components/_classes/component/Component.js#L2302
    # If the defaultValue is empty, then the field will be populated with the emptyValue in the form data.
    return component.get("defaultValue")


def mimetype_allowed(mime_type: str, allowed_mime_types: List[str]) -> bool:
    """
    Test if the file mime type passes the allowed_mime_types Formio configuration.
    """
    #  no allowlist specified -> everything is allowed
    if not allowed_mime_types:
        return True

    # wildcard specified -> everything is allowed
    if "*" in allowed_mime_types:
        return True

    return mime_type in allowed_mime_types


# See https://help.form.io/userguide/forms/form-components#input-mask for the
# semantics, and FormioUtils.getInputMask for the implementation.
def conform_to_mask(value: str, mask: str) -> str:
    """
    Given an input and a Formio mask, try to conform the value to the mask.

    If the value is not compatible with the mask, a ``ValueError`` is raised.
    """
    # loop through all the characters of the value and test them against the mask. Note
    # that the value and mask may have different lengths due to non-input characters
    # such as spaces/dashes... Formio only recognizes alphanumeric inputs as variable
    # user input, the rest is part of the mask.
    # NOTE: we don't check for numeric masks or not, let that be handled by Formio itself

    # the final result characters, build from the value and mask
    result: List[str] = []
    char_index, mask_index = 0, 0
    LOOP_GUARD, iterations = 1000, 0

    # maps the formio mask characters to rules to test for alphanumeric chars etc.
    TEST_RULES = {
        "9": lambda c: c.isnumeric(),
        "A": lambda c: c.isalpha(),
        "a": lambda c: c.isalpha(),
        "*": lambda c: c.isalnum(),
    }

    # the loop indices are reset within an iteration, but in the end either a ValueError
    # is raised because of mismatch with the mask, or the value has been re-formatted
    # conforming to the mask and thus has the same length.
    while len(result) != len(mask):
        if iterations > LOOP_GUARD:  # pragma: nocover
            raise RuntimeError("Infinite while-loop detected!")
        iterations += 1

        try:
            char, mask_char = value[char_index], mask[mask_index]
        except IndexError as exc:
            raise ValueError("Ran out of mask or value characters to process") from exc

        test = TEST_RULES.get(mask_char)

        # check if the character matches the mask - if it does, post-process and put
        # it in the result list
        if test and test(char) is True:
            # check if we need to allow uppercase
            if mask_char.islower() and char.isupper():
                char = char.lower()
            result.append(char)
            # at the end of processing a character, advance the indices for the next
            # character
            char_index += 1
            mask_index += 1
            continue
        elif char == mask_char:  # literal match -> good to go
            result.append(char)
            # at the end of processing a character, advance the indices for the next
            # character
            char_index += 1
            mask_index += 1
            continue
        elif test is not None:  # there is a test, but it didn't pass
            # there was a test, meaning this is an alphanumeric mask of some form. We
            # may potentially skip some separator/formatting chars but ONLY if the
            # current char is not alphanumeric at all. If it is, it doesn't match
            # the expected pattern and we raise a ValueError.
            if char.isalnum():
                raise ValueError(
                    f"Character {char} did not match expected pattern {mask_char}"
                )
            elif mask_char == "*":
                raise ValueError(f"Character {char} was expected to be alphanumeric")
            # at the end of processing a character, advance the indices for the next
            # character
            char_index += 1
            continue
        elif test is None:  # no test -> it's a formatting character
            # if we encounter a formatting character that isn't the current input character,
            # check if the current character is possibly an input (by checking if it's
            # alphanumeric). If it's not, then we have a mismatch, otherwise we insert
            # the formatting character in the result list and process the char again
            # against the next mask char.
            if not char.isalnum():
                raise ValueError(
                    f"Character {char} did not match expected formatting character {mask_char}"
                )

            # the character is probably input, so add the formatter to the result list and
            # keep the current char_index so that we process it again
            result.append(mask_char)
            mask_index += 1
            continue

        else:  # pragma: nocover
            raise RuntimeError(
                f"Unexpected situation! Mask: {mask}, input value: {value}"
            )

    return "".join(result)
