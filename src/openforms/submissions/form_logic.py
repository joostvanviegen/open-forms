from typing import TYPE_CHECKING, Any, Dict

import elasticapm
from json_logic import jsonLogic

from openforms.formio.service import get_dynamic_configuration
from openforms.formio.utils import get_default_values, iter_components
from openforms.forms.constants import LogicActionTypes
from openforms.forms.models import FormLogic
from openforms.prefill import JSONObject

if TYPE_CHECKING:  # pragma: nocover
    from .models import Submission, SubmissionStep


def set_property_value(
    configuration: JSONObject,
    component_key: str,
    property_name: str,
    property_value: str,
) -> JSONObject:
    # iter over the (nested) components, and when we find the specified key, mutate it and break
    # out of the loop
    for component in iter_components(configuration=configuration, recursive=True):
        if component["key"] == component_key:
            component[property_name] = property_value
            break

    return configuration


def get_component(configuration: JSONObject, key: str) -> JSONObject:
    for component in iter_components(configuration=configuration, recursive=True):
        if component["key"] == key:
            return component


@elasticapm.capture_span(span_type="app.submissions.logic")
def evaluate_form_logic(
    submission: "Submission",
    step: "SubmissionStep",
    data: Dict[str, Any],
    dirty=False,
    **context,
) -> Dict[str, Any]:
    """
    Process all the form logic rules and mutate the step configuration if required.
    """
    # grab the configuration that can be **mutated**
    configuration = step.form_step.form_definition.configuration

    # we need to apply the context-specific configurations first before we can apply
    # mutations based on logic, which is then in turn passed to the serializer(s)
    configuration = get_dynamic_configuration(
        configuration,
        # context is expected to contain request, as is the default behaviour with DRF
        # view(set)s and serializers. Note that :func:`get_dynamic_configuration` is
        # planned for refactor as part of #1068, which should drop the ``request``
        # argument. The required information is available on the ``submission`` object
        # already.
        request=context.get("request"),
        submission=submission,
    )

    # check what the default data values are
    defaults = get_default_values(configuration)

    # merge the default values and supplied data - supplied data overwrites defaults
    # if keys are present in both dicts
    data = {**defaults, **data}

    if not step.data:
        step.data = {}

    # ensure this function is idempotent
    _evaluated = getattr(step, "_form_logic_evaluated", False)
    if _evaluated:
        return configuration

    # renderer evaluates logic for all steps at once, so we can avoid repeated queries
    # by caching the rules on the form instance.
    # Note that form.formlogic_set.all() is never cached by django, so we can't rely
    # on that.
    rules = getattr(submission.form, "_cached_logic_rules", None)
    if rules is None:
        rules = FormLogic.objects.filter(form=submission.form)
        submission.form._cached_logic_rules = rules

    submission_state = submission.load_execution_state()

    for rule in rules:
        if jsonLogic(rule.json_logic_trigger, data):
            for action in rule.actions:
                action_details = action["action"]
                if action_details["type"] == LogicActionTypes.value:
                    new_value = jsonLogic(action_details["value"], data)
                    configuration = set_property_value(
                        configuration, action["component"], "value", new_value
                    )
                    step.data[action["component"]] = new_value
                elif action_details["type"] == LogicActionTypes.property:
                    property_name = action_details["property"]["value"]
                    property_value = action_details["state"]
                    set_property_value(
                        configuration,
                        action["component"],
                        property_name,
                        property_value,
                    )
                elif action_details["type"] == LogicActionTypes.disable_next:
                    step._can_submit = False
                elif action_details["type"] == LogicActionTypes.step_not_applicable:
                    submission_step_to_modify = submission_state.resolve_step(
                        action["form_step"]
                    )
                    submission_step_to_modify._is_applicable = False
                    if submission_step_to_modify == step:
                        step._is_applicable = False

    if dirty:
        # only keep the changes in the data, so that old values do not overwrite otherwise
        # debounced client-side data changes
        data_diff = {}
        for key, new_value in step.data.items():
            original_value = data.get(key)
            # Reset the value of any field that may have become hidden again after evaluating the logic
            if original_value:
                component = get_component(configuration, key)
                if (
                    component
                    and component.get("hidden")
                    and component.get("clearOnHide")
                ):
                    data_diff[key] = defaults.get(key, "")
                    continue

            if new_value == original_value:
                continue
            data_diff[key] = new_value

        # only return the 'overrides'
        step.data = data_diff

    step._form_logic_evaluated = True

    return configuration


def check_submission_logic(submission, unsaved_data=None):
    logic_rules = FormLogic.objects.filter(
        form=submission.form,
        actions__contains=[{"action": {"type": LogicActionTypes.step_not_applicable}}],
    )

    merged_data = submission.data
    if unsaved_data:
        merged_data = {**merged_data, **unsaved_data}

    submission_state = submission.load_execution_state()

    for rule in logic_rules:
        if jsonLogic(rule.json_logic_trigger, merged_data):
            for action in rule.actions:
                if action["action"]["type"] != LogicActionTypes.step_not_applicable:
                    continue

                submission_step_to_modify = submission_state.resolve_step(
                    action["form_step"]
                )
                submission_step_to_modify._is_applicable = False
