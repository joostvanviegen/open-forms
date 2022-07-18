from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from openforms.forms.constants import FormVariableDataTypes, FormVariableSources
from openforms.forms.tests.factories import (
    FormFactory,
    FormLogicFactory,
    FormStepFactory,
    FormVariableFactory,
)
from openforms.submissions.tests.mixins import VariablesTestMixin

from ...models import SubmissionValueVariable
from ..factories import SubmissionFactory, SubmissionStepFactory
from ..mixins import SubmissionsMixin


class UpdateVariablesWithLogicTests(VariablesTestMixin, SubmissionsMixin, APITestCase):
    def test_update_data_in_step(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "number",
                        "key": "nGreenApples",
                    },
                    {
                        "type": "number",
                        "key": "nRedApples",
                    },
                    {"type": "number", "key": "totApples"},
                ]
            },
        )

        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "and": [
                    {
                        "!=": [
                            {"var": "nGreenApples"},
                            None,
                        ]
                    },
                    {
                        "!=": [
                            {"var": "nRedApples"},
                            None,
                        ]
                    },
                ]
            },
            actions=[
                {
                    "variable": "totApples",
                    "action": {
                        "name": "Update variable",
                        "type": "variable",
                        "value": {
                            "+": [{"var": "nGreenApples"}, {"var": "nRedApples"}]
                        },
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)

        endpoint = reverse(
            "api:submission-steps-logic-check",
            kwargs={"submission_uuid": submission.uuid, "step_uuid": step1.uuid},
        )
        self._add_submission_to_session(submission)

        response = self.client.post(
            endpoint, data={"data": {"nGreenApples": 3, "nRedApples": 5}}
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            {
                "totApples": 8
            },  # Only the changed data is sent back to the frontend after the logic check
            response.data["step"]["data"],
        )
        # Check that no variables are persisted to the backend because the step has not been submitted yet
        self.assertEqual(
            0, SubmissionValueVariable.objects.filter(submission=submission).count()
        )

    def test_that_updated_data_is_used_by_subsequent_rules(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "number",
                        "key": "nGreenApples",
                    },
                    {
                        "type": "number",
                        "key": "nRedApples",
                    },
                    {"type": "number", "key": "totApples"},
                    {"type": "number", "key": "nPeaches"},
                    {"type": "number", "key": "totFruit"},
                ]
            },
        )

        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "and": [
                    {
                        "!=": [
                            {"var": "nGreenApples"},
                            None,
                        ]
                    },
                    {
                        "!=": [
                            {"var": "nRedApples"},
                            None,
                        ]
                    },
                ]
            },
            actions=[
                {
                    "variable": "totApples",
                    "action": {
                        "name": "Update variable",
                        "type": "variable",
                        "value": {
                            "+": [{"var": "nGreenApples"}, {"var": "nRedApples"}]
                        },
                    },
                }
            ],
        )
        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "and": [
                    {
                        "!=": [
                            {"var": "nGreenApples"},
                            None,
                        ]
                    },
                    {
                        "!=": [
                            {"var": "nRedApples"},
                            None,
                        ]
                    },
                    {
                        "!=": [
                            {"var": "nPeaches"},
                            None,
                        ]
                    },
                ]
            },
            actions=[
                {
                    "variable": "totFruit",
                    "action": {
                        "name": "Update variable",
                        "type": "variable",
                        "value": {
                            "+": [
                                {"var": "totApples"},
                                {"var": "nPeaches"},
                            ]  # This needs to use the calculated value of totApples
                        },
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)

        endpoint = reverse(
            "api:submission-steps-logic-check",
            kwargs={"submission_uuid": submission.uuid, "step_uuid": step1.uuid},
        )
        self._add_submission_to_session(submission)

        response = self.client.post(
            endpoint, data={"data": {"nGreenApples": 3, "nRedApples": 5, "nPeaches": 4}}
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            {
                "totApples": 8,
                "totFruit": 12,
            },  # Only the changed data is sent back to the frontend after the logic check
            response.data["step"]["data"],
        )
        # Check that no variables are persisted to the backend because the step has not been submitted yet
        self.assertEqual(
            0, SubmissionValueVariable.objects.filter(submission=submission).count()
        )

    def test_that_updated_data_is_used_by_subsequent_actions(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "number",
                        "key": "nGreenApples",
                    },
                    {
                        "type": "number",
                        "key": "nRedApples",
                    },
                    {"type": "number", "key": "totApples"},
                    {"type": "number", "key": "nPeaches"},
                    {"type": "number", "key": "totFruit"},
                ]
            },
        )

        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "and": [
                    {
                        "!=": [
                            {"var": "nGreenApples"},
                            None,
                        ]
                    },
                    {
                        "!=": [
                            {"var": "nRedApples"},
                            None,
                        ]
                    },
                    {
                        "!=": [
                            {"var": "nPeaches"},
                            None,
                        ]
                    },
                ]
            },
            actions=[
                {
                    "variable": "totApples",
                    "action": {
                        "name": "Update variable",
                        "type": "variable",
                        "value": {
                            "+": [{"var": "nGreenApples"}, {"var": "nRedApples"}]
                        },
                    },
                },
                {
                    "variable": "totFruit",
                    "action": {
                        "name": "Update variable",
                        "type": "variable",
                        "value": {
                            "+": [
                                {"var": "totApples"},
                                {"var": "nPeaches"},
                            ]  # This needs to use the calculated value of totApples
                        },
                    },
                },
            ],
        )
        submission = SubmissionFactory.create(form=form)

        endpoint = reverse(
            "api:submission-steps-logic-check",
            kwargs={"submission_uuid": submission.uuid, "step_uuid": step1.uuid},
        )
        self._add_submission_to_session(submission)

        response = self.client.post(
            endpoint, data={"data": {"nGreenApples": 3, "nRedApples": 5, "nPeaches": 4}}
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            {
                "totApples": 8,
                "totFruit": 12,
            },  # Only the changed data is sent back to the frontend after the logic check
            response.data["step"]["data"],
        )
        # Check that no variables are persisted to the backend because the step has not been submitted yet
        self.assertEqual(
            0, SubmissionValueVariable.objects.filter(submission=submission).count()
        )

    def test_update_data_based_on_previous_step(self):
        form = FormFactory.create()
        step1 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "number",
                        "key": "nGreenApples",
                    },
                    {
                        "type": "number",
                        "key": "nRedApples",
                    },
                ]
            },
        )
        step2 = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {"type": "number", "key": "nPeaches"},
                    {"type": "number", "key": "totFruit"},
                ]
            },
        )

        FormLogicFactory.create(
            form=form,
            json_logic_trigger={
                "and": [
                    {
                        "!=": [
                            {"var": "nGreenApples"},
                            None,
                        ]
                    },
                    {
                        "!=": [
                            {"var": "nRedApples"},
                            None,
                        ]
                    },
                    {
                        "!=": [
                            {"var": "nPeaches"},
                            None,
                        ]
                    },
                ]
            },
            actions=[
                {
                    "variable": "totFruit",
                    "action": {
                        "name": "Update variable",
                        "type": "variable",
                        "value": {
                            "+": [
                                {"var": "nRedApples"},
                                {"var": "nGreenApples"},
                                {"var": "nPeaches"},
                            ]
                        },
                    },
                }
            ],
        )
        submission = SubmissionFactory.create(form=form)
        SubmissionStepFactory.create(
            submission=submission,
            form_step=step1,
            data={"nGreenApples": 3, "nRedApples": 5},
        )

        endpoint = reverse(
            "api:submission-steps-logic-check",
            kwargs={"submission_uuid": submission.uuid, "step_uuid": step2.uuid},
        )
        self._add_submission_to_session(submission)

        response = self.client.post(endpoint, data={"data": {"nPeaches": 4}})

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            {
                "totFruit": 12,
            },
            response.data["step"]["data"],
        )
        self.assertFalse(
            SubmissionValueVariable.objects.filter(
                submission=submission, key="totFruit"
            ).exists()
        )

    def test_variables_not_related_to_a_step_are_persisted(self):
        form = FormFactory.create()
        form_step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "number",
                        "key": "nGreenApples",
                    },
                    {
                        "type": "number",
                        "key": "nRedApples",
                    },
                ]
            },
        )
        tot_apples_var = FormVariableFactory.create(
            form=form,
            key="totApples",
            source=FormVariableSources.user_defined,
            data_type=FormVariableDataTypes.float,
            form_definition=None,
        )

        submission = SubmissionFactory.create(form=form)

        self._add_submission_to_session(submission)
        endpoint = reverse(
            "api:submission-steps-detail",
            kwargs={
                "submission_uuid": submission.uuid,
                "step_uuid": form_step.uuid,
            },
        )
        body = {
            "data": {"nGreenApples": 3, "nRedApples": 5, "totApples": 8}
        }  # Tot apples is added to the step data during the logic check call

        # Persist the step
        response = self.client.put(endpoint, body)

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        variable = SubmissionValueVariable.objects.filter(
            submission=submission, form_variable=tot_apples_var
        ).first()

        self.assertIsNotNone(variable)
        self.assertEqual(8, variable.value)

    def test_user_defined_variables_are_persisted(self):
        form = FormFactory.create()
        form_step = FormStepFactory.create(
            form=form,
            form_definition__configuration={
                "components": [
                    {
                        "type": "number",
                        "key": "nGreenApples",
                    },
                    {
                        "type": "number",
                        "key": "nRedApples",
                    },
                ]
            },
        )
        tot_apples_var = FormVariableFactory.create(
            form=form,
            key="totApples",
            source=FormVariableSources.user_defined,
            data_type=FormVariableDataTypes.float,
            form_definition=form_step.form_definition,
        )

        submission = SubmissionFactory.create(form=form)

        self._add_submission_to_session(submission)
        endpoint = reverse(
            "api:submission-steps-detail",
            kwargs={
                "submission_uuid": submission.uuid,
                "step_uuid": form_step.uuid,
            },
        )
        body = {
            "data": {"nGreenApples": 3, "nRedApples": 5, "totApples": 8}
        }  # Tot apples is added to the step data during the logic check call

        # Persist the step
        response = self.client.put(endpoint, body)

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        variable = SubmissionValueVariable.objects.filter(
            submission=submission, form_variable=tot_apples_var
        ).first()

        self.assertIsNotNone(variable)
        self.assertEqual(8, variable.value)
