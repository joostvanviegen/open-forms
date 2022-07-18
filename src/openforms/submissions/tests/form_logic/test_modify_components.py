from django.test import TestCase

from freezegun import freeze_time
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from openforms.forms.constants import LogicActionTypes
from openforms.forms.tests.factories import (
    FormFactory,
    FormLogicFactory,
    FormStepFactory,
)
from openforms.logging.models import TimelineLogProxy

from ...form_logic import evaluate_form_logic
from ..factories import SubmissionFactory, SubmissionStepFactory
from ..mixins import SubmissionsMixin, VariablesTestMixin


class ComponentModificationTests(VariablesTestMixin, TestCase):
    def test_change_component_to_hidden(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "step1_textfield1",
                    }
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "step2_textfield1",
                        "hidden": False,
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "==": [
                    {"var": "step1_textfield1"},
                    "hide step 2",
                ]
            },
            actions=[
                {
                    "component": "step2_textfield1",
                    "action": {
                        "name": "Hide element",
                        "type": "property",
                        "property": {
                            "type": "bool",
                            "value": "hidden",
                        },
                        "state": True,
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={"step1_textfield1": "hide step 2"},
        )
        # not saved in DB!
        submission_step_2 = SubmissionStepFactory.build(
            submission=submission,
            form_step=step2,
        )

        configuration = evaluate_form_logic(
            submission, submission_step_2, submission.data
        )

        expected = {
            "components": [
                {
                    "type": "textfield",
                    "key": "step2_textfield1",
                    "hidden": True,
                }
            ]
        }
        self.assertEqual(configuration, expected)

    def test_hiding_component_empties_its_data(self):
        form = FormFactory.create()
        form_step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "component1",
                        "hidden": False,
                        "clearOnHide": True,
                    },
                    {
                        "type": "textfield",
                        "key": "component2",
                        "hidden": False,
                        "clearOnHide": True,
                    },
                ]
            },
        )

        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "==": [
                    {"var": "component1"},
                    "trigger value",
                ]
            },
            actions=[
                {
                    "component": "component2",
                    "action": {
                        "name": "Hide element",
                        "type": "property",
                        "property": {
                            "type": "bool",
                            "value": "hidden",
                        },
                        "state": True,
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission,
            form_step=form_step,
            data={
                "component1": "trigger value",
                "component2": "Some data to be deleted",
            },
        )

        configuration = evaluate_form_logic(
            submission, submission_step, submission.data, dirty=True
        )

        expected = {
            "components": [
                {
                    "type": "textfield",
                    "key": "component1",
                    "hidden": False,
                    "clearOnHide": True,
                },
                {
                    "type": "textfield",
                    "key": "component2",
                    "hidden": True,
                    "clearOnHide": True,
                },
            ]
        }
        self.assertEqual(configuration, expected)
        self.assertEqual("", submission_step.data["component2"])

    def test_change_component_to_required(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "name",
                    }
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "surname",
                        "validate": {"required": False},
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "==": [
                    {"var": "name"},
                    "john",
                ]
            },
            actions=[
                {
                    "component": "surname",
                    "action": {
                        "name": "Make required",
                        "type": "property",
                        "property": {
                            "type": "object",
                            "value": "validate",
                        },
                        "state": {"required": True},
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={"name": "john"},
        )
        # not saved in DB!
        submission_step_2 = SubmissionStepFactory.build(
            submission=submission,
            form_step=step2,
        )

        configuration = evaluate_form_logic(
            submission, submission_step_2, submission.data
        )

        expected = {
            "components": [
                {
                    "type": "textfield",
                    "key": "surname",
                    "validate": {"required": True},
                }
            ]
        }
        self.assertEqual(configuration, expected)

    def test_change_component_to_hidden_if_text_contains(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "fooBarBaz",
                    }
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "test",
                        "hidden": True,
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "in": [
                    {"var": "fooBarBaz"},
                    "foobarbaz",
                ]
            },
            actions=[
                {
                    "component": "test",
                    "action": {
                        "name": "Make element visible",
                        "type": "property",
                        "property": {
                            "type": "bool",
                            "value": "hidden",
                        },
                        "state": False,
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={"fooBarBaz": "foo"},
        )
        # not saved in DB!
        submission_step_2 = SubmissionStepFactory.build(
            submission=submission,
            form_step=step2,
        )

        configuration = evaluate_form_logic(
            submission, submission_step_2, submission.data
        )

        expected = {
            "components": [
                {
                    "type": "textfield",
                    "key": "test",
                    "hidden": False,
                }
            ]
        }
        self.assertEqual(configuration, expected)

    def test_change_component_to_hidden_if_array_contains(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "email",
                        "key": "userEmail",
                    }
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "test",
                        "hidden": True,
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "in": [
                    {"var": "userEmail"},
                    ["test1@example.com", "test2@example.com"],
                ]
            },
            actions=[
                {
                    "component": "test",
                    "action": {
                        "name": "Make element visible",
                        "type": "property",
                        "property": {
                            "type": "bool",
                            "value": "hidden",
                        },
                        "state": False,
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={"userEmail": "test1@example.com"},
        )
        # not saved in DB!
        submission_step_2 = SubmissionStepFactory.build(
            submission=submission,
            form_step=step2,
        )

        configuration = evaluate_form_logic(
            submission, submission_step_2, submission.data
        )

        expected = {
            "components": [
                {
                    "type": "textfield",
                    "key": "test",
                    "hidden": False,
                }
            ]
        }
        self.assertEqual(configuration, expected)

    def test_dont_change_component_to_hidden_if_text_does_not_contain(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "fooBarBaz",
                    }
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "test",
                        "hidden": True,
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "in": [
                    {"var": "fooBarBaz"},
                    "foobarbaz",
                ]
            },
            actions=[
                {
                    "component": "test",
                    "action": {
                        "name": "Make element visible",
                        "type": "property",
                        "property": {
                            "type": "bool",
                            "value": "hidden",
                        },
                        "state": False,
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={"fooBarBaz": "hello"},
        )
        # not saved in DB!
        submission_step_2 = SubmissionStepFactory.build(
            submission=submission,
            form_step=step2,
        )

        configuration = evaluate_form_logic(
            submission, submission_step_2, submission.data
        )

        expected = {
            "components": [
                {
                    "type": "textfield",
                    "key": "test",
                    "hidden": True,
                }
            ]
        }
        self.assertEqual(configuration, expected)

    def test_dont_change_component_to_hidden_if_array_does_not_contain(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "email",
                        "key": "userEmail",
                    }
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "test",
                        "hidden": True,
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "in": [
                    {"var": "userEmail"},
                    ["test1@example.com", "test2@example.com"],
                ]
            },
            actions=[
                {
                    "component": "test",
                    "action": {
                        "name": "Make element visible",
                        "type": "property",
                        "property": {
                            "type": "bool",
                            "value": "hidden",
                        },
                        "state": False,
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={"userEmail": "test3@example.com"},
        )
        # not saved in DB!
        submission_step_2 = SubmissionStepFactory.build(
            submission=submission,
            form_step=step2,
        )

        configuration = evaluate_form_logic(
            submission, submission_step_2, submission.data
        )

        expected = {
            "components": [
                {
                    "type": "textfield",
                    "key": "test",
                    "hidden": True,
                }
            ]
        }
        self.assertEqual(configuration, expected)

    def test_extract_value(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "step1_textfield1",
                    }
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "step2_textfield1",
                        "hidden": False,
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={"==": [1, 1]},
            actions=[
                {
                    "component": "step2_textfield1",
                    "action": {
                        "name": "Set extracted value",
                        "type": "value",
                        "value": {"var": "step1_textfield1"},
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={"step1_textfield1": "some value"},
        )
        # not saved in DB!
        submission_step_2 = SubmissionStepFactory.build(
            submission=submission,
            form_step=step2,
        )

        configuration = evaluate_form_logic(
            submission, submission_step_2, submission.data
        )

        expected = {
            "components": [
                {
                    "type": "textfield",
                    "key": "step2_textfield1",
                    "hidden": False,
                    "value": "some value",
                }
            ]
        }
        self.assertEqual(configuration, expected)
        self.assertEqual({"step2_textfield1": "some value"}, submission_step_2.data)

    def test_evaluate_logic_with_empty_data(self):
        """
        When the SDK first loads a form, it does an evaluation of the logic with an empty dict of data.
        In subsequent evaluations of the logic, the dict with the data may still not contain all the values,
        since they haven't been filled in yet.
        """
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "name",
                    }
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "surname",
                        "validate": {"required": False},
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "==": [
                    {"var": "name"},
                    "john",
                ]
            },
            actions=[
                {
                    "component": "surname",
                    "action": {
                        "name": "Make required",
                        "type": "property",
                        "property": {
                            "type": "json",
                            "value": "validate",
                        },
                        "state": {"required": True},
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={},  # Empty data!
        )
        # not saved in DB!
        submission_step_2 = SubmissionStepFactory.build(
            submission=submission,
            form_step=step2,
        )

        configuration = evaluate_form_logic(
            submission, submission_step_2, submission.data
        )

        # Expect configuration unchanged
        expected = {
            "components": [
                {
                    "type": "textfield",
                    "key": "surname",
                    "validate": {"required": False},
                }
            ]
        }
        self.assertEqual(configuration, expected)

    def test_change_component_with_nested_components(self):
        form = FormFactory.create()
        step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "key": "Cat1",
                        "type": "fieldset",
                        "label": "Cat 1",
                        "legend": "Cat 1",
                        "hidden": False,
                        "components": [
                            {
                                "key": "CatBirthDate",
                                "type": "date",
                                "format": "dd-MM-yyyy",
                                "hidden": False,
                            },
                            {
                                "key": "addAnotherCat",
                                "type": "radio",
                                "hidden": False,
                                "values": [
                                    {"label": "Yes", "value": "yes"},
                                    {"label": "No", "value": "no"},
                                ],
                            },
                        ],
                    },
                    {
                        "key": "Cat2",
                        "type": "fieldset",
                        "label": "Cat 2",
                        "legend": "Cat 2",
                        "hidden": False,
                        "components": [
                            {
                                "key": "CatBirthDate2",
                                "type": "date",
                                "format": "dd-MM-yyyy",
                                "hidden": False,
                            }
                        ],
                    },
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={"!=": [{"var": "addAnotherCat"}, "yes"]},
            actions=[
                {
                    "formStep": None,
                    "component": "Cat2",
                    "action": {
                        "type": "property",
                        "property": {"value": "hidden", "type": "bool"},
                        "value": {},
                        "state": True,
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission,
            form_step=step,
            data={},
        )

        configuration = evaluate_form_logic(
            submission, submission_step, submission.data
        )

        self.assertTrue(configuration["components"][1]["hidden"])


class StepModificationTests(VariablesTestMixin, TestCase):
    def test_next_button_disabled(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "step1_textfield1",
                    }
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "step2_textfield1",
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "==": [
                    {"var": "step1_textfield1"},
                    "disable next button",
                ]
            },
            actions=[
                {
                    "component": "step2_textfield1",
                    "action": {
                        "name": "Hide element",
                        "type": "disable-next",
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={"step1_textfield1": "disable next button"},
        )
        # not saved in DB!
        submission_step_2 = SubmissionStepFactory.build(
            submission=submission,
            form_step=step2,
        )

        self.assertTrue(submission_step_2.can_submit)

        evaluate_form_logic(submission, submission_step_2, submission.data)

        self.assertFalse(submission_step_2.can_submit)

    def test_step_not_applicable(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "number",
                        "key": "age",
                    }
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "driverId",
                    }
                ]
            },
        )
        form_step2_path = reverse(
            "api:form-steps-detail",
            kwargs={"form_uuid_or_slug": form.uuid, "uuid": step2.uuid},
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "<": [
                    {"var": "age"},
                    18,
                ]
            },
            actions=[
                {
                    "form_step": f"http://example.com{form_step2_path}",
                    "action": {
                        "name": "Step is not applicable",
                        "type": "step-not-applicable",
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step_1 = SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={"age": 16},
        )
        # not saved in DB!
        submission_step_2 = SubmissionStepFactory.build(
            submission=submission,
            form_step=step2,
        )

        self.assertTrue(submission_step_2.is_applicable)

        evaluate_form_logic(submission, submission_step_1, submission.data)
        submission_state = submission.load_execution_state()
        updated_step_2 = submission_state.get_submission_step(
            form_step_uuid=str(step2.uuid)
        )

        self.assertFalse(updated_step_2.is_applicable)

    def test_date_trigger(self):
        form = FormFactory.create()
        step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "date",
                        "key": "dateOfBirth",
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "<": [
                    {"date": {"var": "dateOfBirth"}},
                    {"date": "2021-01-01"},
                ]
            },
            actions=[
                {
                    "action": {
                        "name": "Disable next",
                        "type": "disable-next",
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission,
            form_step=step,
            data={"dateOfBirth": "2020-01-01"},
        )

        self.assertTrue(submission_step.can_submit)

        evaluate_form_logic(submission, submission_step, submission.data)

        self.assertFalse(submission_step.can_submit)

    def test_date_of_birth_trigger(self):
        form = FormFactory.create()
        step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "date",
                        "key": "dateOfBirth",
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                ">": [
                    {"date": {"var": "dateOfBirth"}},
                    {"-": [{"today": []}, {"rdelta": [18]}]},
                ]
            },
            actions=[
                {
                    "action": {
                        "name": "Disable next",
                        "type": "disable-next",
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission,
            form_step=step,
            data={"dateOfBirth": "2003-01-01"},
        )

        self.assertTrue(submission_step.can_submit)

        with freeze_time("2020-01-01"):
            evaluate_form_logic(submission, submission_step, submission.data)

        self.assertFalse(submission_step.can_submit)

    def test_dirty_data_only_diff_data_returned(self):
        form = FormFactory.create()
        step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "name",
                    },
                    {
                        "type": "textfield",
                        "key": "changingKey",
                    },
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "==": [
                    {"var": "name"},
                    "john",
                ]
            },
            actions=[
                {
                    "component": "changingKey",
                    "action": {
                        "name": "Set value",
                        "type": LogicActionTypes.value,
                        "value": "changed",
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission, form_step=step, data={}
        )
        dirty_data = {
            "name": "john",
            "changingKey": "original",
        }

        evaluate_form_logic(submission, submission_step, dirty_data)

        self.assertEqual(
            submission_step.data,
            {"changingKey": "changed"},
        )

    def test_select_boxes_trigger(self):
        form = FormFactory.create()
        step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "selectboxes",
                        "key": "currentPets",
                        "values": [
                            {"label": "Cat", "value": "cat"},
                            {"label": "Dog", "value": "dog"},
                            {"label": "Fish", "value": "fish"},
                        ],
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "==": [
                    {"var": "currentPets.cat"},
                    True,
                ]
            },
            actions=[
                {
                    "action": {
                        "name": "Disable next",
                        "type": "disable-next",
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission,
            form_step=step,
            data={"currentPets": {"cat": True, "dog": False, "fish": False}},
        )

        self.assertTrue(submission_step.can_submit)

        evaluate_form_logic(submission, submission_step, submission.data)

        self.assertFalse(submission_step.can_submit)

    def test_select_boxes_trigger_with_dot_in_key_name(self):
        form = FormFactory.create()
        step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "selectboxes",
                        "key": "current.pets",
                        "values": [
                            {"label": "Cat", "value": "cat"},
                            {"label": "Dog", "value": "dog"},
                            {"label": "Fish", "value": "fish"},
                        ],
                    }
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "==": [
                    {"var": "current.pets.cat"},
                    True,
                ]
            },
            actions=[
                {
                    "action": {
                        "name": "Disable next",
                        "type": "disable-next",
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission,
            form_step=step,
            data={"current": {"pets": {"cat": True, "dog": False, "fish": False}}},
        )

        self.assertTrue(submission_step.can_submit)

        evaluate_form_logic(submission, submission_step, submission.data)

        self.assertFalse(submission_step.can_submit)

    def test_normal_component_trigger_with_dot_in_key_name(self):
        form = FormFactory.create()
        step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [{"key": "normal.component", "type": "textfield"}]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "==": [
                    {"var": "normal.component"},
                    "test-value",
                ]
            },
            actions=[
                {
                    "action": {
                        "name": "Disable next",
                        "type": "disable-next",
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission,
            form_step=step,
            data={"normal": {"component": "test-value"}},
        )

        self.assertTrue(submission_step.can_submit)

        evaluate_form_logic(submission, submission_step, submission.data)

        self.assertFalse(submission_step.can_submit)

    def test_component_removed_from_definition(self):
        # Test for issue #1568
        form = FormFactory.create()
        step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "name",
                    },
                ]
            },
        )

        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission,
            form_step=step,
            data={
                "name": "Jane",
                "surname": "Doe",
            },  # Data for component no longer in the definition
        )

        # This shouldn't raise an error
        evaluate_form_logic(
            submission, submission_step, submission_step.data, dirty=True
        )


class CheckLogicSubmissionTest(VariablesTestMixin, SubmissionsMixin, APITestCase):
    def test_response_contains_submission(self):
        form = FormFactory.create()
        form_step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "date",
                        "key": "dateOfBirth",
                    }
                ]
            },
        )
        form_step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "driving",
                    }
                ]
            },
        )
        form_step2_path = reverse(
            "api:form-steps-detail",
            kwargs={"form_uuid_or_slug": form.uuid, "uuid": form_step2.uuid},
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                ">": [
                    {"date": {"var": "dateOfBirth"}},
                    {"-": [{"today": []}, {"rdelta": [18]}]},
                ]
            },
            actions=[
                {
                    "form_step": f"http://example.com{form_step2_path}",
                    "action": {
                        "name": "Make step not applicable",
                        "type": "step-not-applicable",
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=form_step1,
            data={"dateOfBirth": "2003-01-01"},
        )
        endpoint = reverse(
            "api:submission-steps-logic-check",
            kwargs={"submission_uuid": submission.uuid, "step_uuid": form_step1.uuid},
        )
        self._add_submission_to_session(submission)

        with freeze_time("2015-10-10"):
            response = self.client.post(
                endpoint, {"data": submission.get_merged_data()}
            )

        submission_details = response.json()

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertFalse(submission_details["submission"]["steps"][1]["isApplicable"])

    def test_with_default_values(self):
        form = FormFactory.create(
            generate_minimal_setup=True,
            formstep__form_definition__configuration={
                "components": [
                    {
                        "type": "checkbox",
                        "key": "hide",
                        "defaultValue": True,
                    },
                    {
                        "type": "textfield",
                        "key": "when-unchecked",
                        "hidden": False,
                    },
                    {
                        "type": "textfield",
                        "key": "when-checked",
                        "hidden": False,
                    },
                ]
            },
        )
        # display checked textfield when checkbox is checked, hide the unchecked one
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={"==": [{"var": "hide"}, True]},
            actions=[
                {
                    "formStep": None,
                    "component": "when-unchecked",
                    "action": {
                        "type": "property",
                        "property": {"value": "hidden", "type": "bool"},
                        "value": {},
                        "state": True,
                    },
                },
                {
                    "formStep": None,
                    "component": "when-checked",
                    "action": {
                        "type": "property",
                        "property": {"value": "hidden", "type": "bool"},
                        "value": {},
                        "state": False,
                    },
                },
            ],
        )
        # hide checked textfield when checkbox is unchecked, display the unchecked one
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={"==": [{"var": "hide"}, False]},
            actions=[
                {
                    "formStep": None,
                    "component": "when-unchecked",
                    "action": {
                        "type": "property",
                        "property": {"value": "hidden", "type": "bool"},
                        "value": {},
                        "state": False,
                    },
                },
                {
                    "formStep": None,
                    "component": "when-checked",
                    "action": {
                        "type": "property",
                        "property": {"value": "hidden", "type": "bool"},
                        "value": {},
                        "state": True,
                    },
                },
            ],
        )
        submission = SubmissionFactory.create(form=form)
        self._add_submission_to_session(submission)
        url_kwargs = {
            "submission_uuid": submission.uuid,
            "step_uuid": form.formstep_set.get().uuid,
        }
        endpoint = reverse("api:submission-steps-detail", kwargs=url_kwargs)
        logic_check_endpoint = reverse(
            "api:submission-steps-logic-check", kwargs=url_kwargs
        )

        with self.subTest("Initial call without data"):
            response = self.client.get(endpoint)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            configuration = response.json()["formStep"]["configuration"]
            self.assertEqual(
                configuration["components"][1],
                {
                    "key": "when-unchecked",
                    "type": "textfield",
                    "hidden": True,
                },
            )
            self.assertEqual(
                configuration["components"][2],
                {
                    "key": "when-checked",
                    "type": "textfield",
                    "hidden": False,
                },
            )

        with self.subTest("On explicit un-check"):
            response = self.client.post(logic_check_endpoint, {"data": {"hide": False}})

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            configuration = response.json()["step"]["formStep"]["configuration"]
            self.assertEqual(
                configuration["components"][1],
                {
                    "key": "when-unchecked",
                    "type": "textfield",
                    "hidden": False,
                },
            )
            self.assertEqual(
                configuration["components"][2],
                {
                    "key": "when-checked",
                    "type": "textfield",
                    "hidden": True,
                },
            )

        with self.subTest("On explicit check"):
            response = self.client.post(logic_check_endpoint, {"data": {"hide": True}})

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            configuration = response.json()["step"]["formStep"]["configuration"]
            self.assertEqual(
                configuration["components"][1],
                {
                    "key": "when-unchecked",
                    "type": "textfield",
                    "hidden": True,
                },
            )
            self.assertEqual(
                configuration["components"][2],
                {
                    "key": "when-checked",
                    "type": "textfield",
                    "hidden": False,
                },
            )


class EvaluateLogicSubmissionTest(VariablesTestMixin, SubmissionsMixin, APITestCase):
    def test_evaluate_logic_with_default_values(self):
        form = FormFactory.create(
            generate_minimal_setup=True,
            formstep__form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "name",
                        "defaultValue": "some-default",
                    },
                    {
                        "type": "textfield",
                        "key": "optional",
                        "hidden": False,
                    },
                ]
            },
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={"==": [{"var": "name"}, "some-default"]},
            actions=[
                {
                    "formStep": None,
                    "component": "optional",
                    "action": {
                        "type": "property",
                        "property": {"value": "hidden", "type": "bool"},
                        "value": {},
                        "state": True,
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        endpoint = reverse(
            "api:submission-steps-detail",
            kwargs={
                "submission_uuid": submission.uuid,
                "step_uuid": form.formstep_set.get().uuid,
            },
        )
        self._add_submission_to_session(submission)

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        configuration = response.json()["formStep"]["configuration"]
        self.assertEqual(
            configuration["components"][1],
            {
                "key": "optional",
                "type": "textfield",
                "hidden": True,
            },
        )

    def test_evaluate_logic_log_event_triggered(self):
        form = FormFactory.create()
        form_step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "firstname",
                        "hidden": False,
                        "clearOnHide": True,
                    },
                    {
                        "type": "date",
                        "key": "birthdate",
                        "hidden": False,
                        "clearOnHide": True,
                    },
                ]
            },
        )

        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                ">": [{"date": {"var": "birthdate"}}, {"date": "2022-06-20"}]
            },
            actions=[
                {
                    "component": "firstname",
                    "formStep": "",
                    "action": {
                        "type": "property",
                        "property": {"value": "disabled", "type": "bool"},
                        "state": True,
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission,
            form_step=form_step,
            data={
                "firstname": "foo",
                "birthdate": "2022-06-21",
            },
        )

        evaluate_form_logic(submission, submission_step, submission.get_merged_data())

        logs = TimelineLogProxy.objects.all()
        self.assertEqual(1, logs.count())
        log = logs[0]
        self.assertTrue(log.extra_data["log_evaluated_rules"][0]["trigger"])

    def test_evaluate_logic_log_event_not_triggered(self):
        form = FormFactory.create()
        form_step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "textfield",
                        "key": "firstname",
                        "hidden": False,
                        "clearOnHide": True,
                    },
                    {
                        "type": "date",
                        "key": "birthdate",
                        "hidden": False,
                        "clearOnHide": True,
                    },
                ]
            },
        )

        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                ">": [{"date": {"var": "birthdate"}}, {"date": "2022-06-20"}]
            },
            actions=[
                {
                    "component": "firstname",
                    "formStep": "",
                    "action": {
                        "type": "property",
                        "property": {"value": "disabled", "type": "bool"},
                        "state": True,
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        submission_step = SubmissionStepFactory.create(
            submission=submission,
            form_step=form_step,
            data={
                "firstname": "foo",
                "birthdate": "2022-06-19",
            },
        )

        evaluate_form_logic(submission, submission_step, submission.get_merged_data())

        logs = TimelineLogProxy.objects.all()
        self.assertEqual(1, logs.count())
        log = logs[0]
        self.assertFalse(log.extra_data["log_evaluated_rules"][0]["trigger"])
