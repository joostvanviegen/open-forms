from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from glom import Assign, PathAccessError, glom

from openforms.forms.models.form_variable import FormVariable

from ..constants import SubmissionValueVariableSources
from .submission import Submission

if TYPE_CHECKING:  # pragma: nocover
    from .submission_step import SubmissionStep


@dataclass
class SubmissionValueVariablesState:
    submission: "Submission"
    _variables: Dict[str, "SubmissionValueVariable"] = None

    def __init__(self, submission: "Submission"):
        self.submission = submission

    @property
    def variables(self) -> Dict[str, "SubmissionValueVariable"]:
        if not self._variables:
            self._variables = self.collect_variables(self.submission)
        return self._variables

    @property
    def saved_variables(self) -> Dict[str, "SubmissionValueVariable"]:
        return {
            variable_key: variable
            for variable_key, variable in self.variables.items()
            if variable.pk
        }

    def get_variable(self, key: str) -> "SubmissionValueVariable":
        return self.variables[key]

    def get_data(
        self,
        submission_step: Optional["SubmissionStep"] = None,
        return_unchanged_data: bool = True,
    ) -> dict:
        submission_variables = self.saved_variables
        if submission_step:
            submission_variables = self.get_variables_in_submission_step(
                submission_step, include_unsaved=False
            )

        data = {}
        for variable_key, variable in submission_variables.items():
            if (
                variable.value is None
                and variable.form_variable
                and variable.value == variable.form_variable.initial_value
                and not return_unchanged_data
            ):
                continue

            if variable.source != SubmissionValueVariableSources.sensitive_data_cleaner:
                glom(data, Assign(variable_key, variable.value, missing=dict))
        return data

    def get_variables_in_submission_step(
        self,
        submission_step: "SubmissionStep",
        include_unsaved=True,
    ) -> Dict[str, "SubmissionValueVariable"]:
        form_definition = submission_step.form_step.form_definition

        variables = self.variables
        if not include_unsaved:
            variables = self.saved_variables

        return {
            variable_key: variable
            for variable_key, variable in variables.items()
            if variable.form_variable
            and variable.form_variable.form_definition == form_definition
        }

    def get_variables_unrelated_to_a_step(self) -> Dict[str, "SubmissionValueVariable"]:
        return {
            variable_key: variable
            for variable_key, variable in self.variables.items()
            if not variable.form_variable.form_definition
        }

    def collect_variables(
        self, submission: "Submission"
    ) -> Dict[str, "SubmissionValueVariable"]:
        # Get the SubmissionValueVariables already saved in the database
        saved_submission_value_variables = (
            submission.submissionvaluevariable_set.all().select_related(
                "form_variable__form_definition"
            )
        )

        # Get all the form variables for the SubmissionVariables that have not been created yet
        form_variables = FormVariable.objects.filter(
            ~Q(
                id__in=saved_submission_value_variables.values_list(
                    "form_variable__id", flat=True
                )
            ),
            form=submission.form,
        ).select_related("form_definition")

        unsaved_value_variables = {}
        for form_variable in form_variables:
            # TODO Fill source field
            key = form_variable.key
            unsaved_submission_var = SubmissionValueVariable(
                submission=submission,
                form_variable=form_variable,
                key=key,
                value=form_variable.get_initial_value(),
            )
            unsaved_value_variables[key] = unsaved_submission_var

        return {
            **{variable.key: variable for variable in saved_submission_value_variables},
            **unsaved_value_variables,
        }

    def remove_variables(self, keys: list) -> None:
        for key in keys:
            if key in self._variables:
                del self._variables[key]


class SubmissionValueVariableManager(models.Manager):
    def bulk_create_or_update_from_data(
        self,
        data: dict,
        submission: "Submission",
        submission_step: "SubmissionStep" = None,
        update_missing_variables: bool = False,
    ) -> None:

        submission_value_variables_state = (
            submission.load_submission_value_variables_state()
        )
        submission_variables = submission_value_variables_state.variables
        if submission_step:
            submission_variables = (
                submission_value_variables_state.get_variables_in_submission_step(
                    submission_step
                )
            )

        variables_to_create = []
        variables_to_update = []
        variables_keys_to_delete = []
        for key, variable in submission_variables.items():
            try:
                variable.value = glom(data, key)
            except PathAccessError:
                if update_missing_variables:
                    if variable.pk:
                        variables_keys_to_delete.append(variable.key)
                    else:
                        variable.value = variable.form_variable.get_initial_value()
                    continue

            if not variable.pk:
                variables_to_create.append(variable)
            else:
                variables_to_update.append(variable)

        self.bulk_create(variables_to_create)
        self.bulk_update(variables_to_update, fields=["value"])
        self.filter(submission=submission, key__in=variables_keys_to_delete).delete()

        # Variables that are deleted are not automatically updated in the state
        # (i.e. they remain present with their pk)
        if variables_keys_to_delete:
            submission_value_variables_state.remove_variables(
                keys=variables_keys_to_delete
            )


class SubmissionValueVariable(models.Model):
    submission = models.ForeignKey(
        to=Submission,
        verbose_name=_("submission"),
        help_text=_("The submission to which this variable value is related"),
        on_delete=models.CASCADE,
    )
    form_variable = models.ForeignKey(
        to=FormVariable,
        verbose_name=_("form variable"),
        help_text=_("The form variable to which this value is related"),
        on_delete=models.SET_NULL,  # In case form definitions are edited after a user has filled in a form.
        null=True,
    )
    # Added for the case where a FormVariable has been deleted, but there is still a SubmissionValueValue.
    # Having a key will help debug where the SubmissionValueValue came from
    key = models.TextField(
        verbose_name=_("key"),
        help_text=_("Key of the variable"),
    )
    value = models.JSONField(
        verbose_name=_("value"),
        help_text=_("The value of the variable"),
        null=True,
        blank=True,
    )
    source = models.CharField(
        verbose_name=_("source"),
        help_text=_("Where variable value came from"),
        choices=SubmissionValueVariableSources.choices,
        max_length=50,
    )
    language = models.CharField(
        verbose_name=_("language"),
        help_text=_("If this value contains text, in which language is it?"),
        max_length=50,
        blank=True,
    )
    created_at = models.DateTimeField(
        verbose_name=_("created at"),
        help_text=_("The date/time at which the value of this variable was created"),
        auto_now_add=True,
    )
    modified_at = models.DateTimeField(
        verbose_name=_("modified at"),
        help_text=_("The date/time at which the value of this variable was last set"),
        null=True,
        blank=True,
        auto_now=True,
    )

    objects = SubmissionValueVariableManager()

    class Meta:
        verbose_name = _("Submission value variable")
        verbose_name_plural = _("Submission values variables")
        unique_together = [["submission", "key"], ["submission", "form_variable"]]

    def __str__(self):
        if self.form_variable:
            return _("Submission value variable {name}").format(
                name=self.form_variable.name
            )
        return _("Submission value variable {key}").format(key=self.key)
