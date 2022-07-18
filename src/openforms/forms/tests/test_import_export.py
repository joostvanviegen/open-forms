import json
import os
import zipfile

from django.core.management import call_command
from django.test import TestCase, override_settings

from openforms.payments.contrib.ogone.tests.factories import OgoneMerchantFactory
from openforms.products.tests.factories import ProductFactory

from ..constants import FormVariableSources
from ..models import Form, FormDefinition, FormLogic, FormStep
from .factories import (
    FormDefinitionFactory,
    FormFactory,
    FormLogicFactory,
    FormStepFactory,
    FormVariableFactory,
)

PATH = os.path.abspath(os.path.dirname(__file__))


class ImportExportTests(TestCase):
    def setUp(self):
        self.filepath = os.path.join(PATH, "export_test.zip")

        def remove_file():
            try:
                os.remove(self.filepath)
            except Exception:
                pass

        self.addCleanup(remove_file)

    @override_settings(ALLOWED_HOSTS=["example.com"])
    def test_export(self):
        form, _ = FormFactory.create_batch(2, authentication_backends=["demo"])
        form_definition, _ = FormDefinitionFactory.create_batch(2)
        FormStepFactory.create(form=form, form_definition=form_definition)
        FormStepFactory.create()
        FormLogicFactory.create(
            form=form,
            actions=[
                {
                    "component": "test_component",
                    "action": {
                        "type": "disable-next",
                    },
                }
            ],
        )
        FormVariableFactory.create(
            form=form, source=FormVariableSources.user_defined, key="test-user-defined"
        )
        FormVariableFactory.create(
            form=form, source=FormVariableSources.static, key="test-static"
        )

        call_command("export", form.pk, self.filepath)

        with zipfile.ZipFile(self.filepath, "r") as f:
            self.assertEqual(
                f.namelist(),
                [
                    "forms.json",
                    "formSteps.json",
                    "formDefinitions.json",
                    "formLogic.json",
                    "formVariables.json",
                ],
            )

            forms = json.loads(f.read("forms.json"))
            self.assertEqual(len(forms), 1)
            self.assertEqual(forms[0]["uuid"], str(form.uuid))
            self.assertEqual(forms[0]["name"], form.name)
            self.assertEqual(forms[0]["internal_name"], form.internal_name)
            self.assertEqual(forms[0]["slug"], form.slug)
            self.assertEqual(forms[0]["authentication_backends"], ["demo"])
            self.assertEqual(len(forms[0]["steps"]), form.formstep_set.count())
            self.assertIsNone(forms[0]["product"])

            form_definitions = json.loads(f.read("formDefinitions.json"))
            self.assertEqual(len(form_definitions), 1)
            self.assertEqual(form_definitions[0]["uuid"], str(form_definition.uuid))
            self.assertEqual(form_definitions[0]["name"], form_definition.name)
            self.assertEqual(
                form_definitions[0]["internal_name"], form_definition.internal_name
            )
            self.assertEqual(form_definitions[0]["slug"], form_definition.slug)
            self.assertEqual(
                form_definitions[0]["configuration"],
                form_definition.configuration,
            )

            form_steps = json.loads(f.read("formSteps.json"))
            self.assertEqual(len(form_steps), 1)
            self.assertEqual(
                form_steps[0]["configuration"], form_definition.configuration
            )

            form_logic = json.loads(f.read("formLogic.json"))
            self.assertEqual(1, len(form_logic))
            self.assertEqual("test_component", form_logic[0]["actions"][0]["component"])
            self.assertEqual(
                {"type": "disable-next"}, form_logic[0]["actions"][0]["action"]
            )
            self.assertIn(str(form.uuid), form_logic[0]["form"])

            form_variables = json.loads(f.read("formVariables.json"))
            # Only user defined form variables are included in the export
            self.assertEqual(len(form_variables), 1)
            self.assertEqual(
                FormVariableSources.user_defined, form_variables[0]["source"]
            )

    def test_import(self):
        product = ProductFactory.create()
        merchant = OgoneMerchantFactory.create()
        form = FormFactory.create(
            product=product,
            authentication_backends=["digid"],
            registration_backend="email",
            registration_backend_options={
                "to_emails": ["foo@bar.baz"],
                "attach_files_to_email": None,
            },
            payment_backend="ogone-legacy",
            payment_backend_options={"merchant_id": merchant.id},
        )
        form_definition = FormDefinitionFactory.create(
            configuration={"components": [{"key": "test-key", "type": "textfield"}]}
        )
        form_step = FormStepFactory.create(form=form, form_definition=form_definition)
        form_logic = FormLogicFactory.create(form=form)

        form_pk, form_definition_pk, form_step_pk, form_logic_pk = (
            form.pk,
            form_definition.pk,
            form_step.pk,
            form_logic.pk,
        )

        call_command("export", form.pk, self.filepath)

        old_form_definition_slug = form_definition.slug
        form_definition.slug = "modified"
        form_definition.save()

        old_form_slug = form.slug
        form.slug = "modified"
        form.save()

        call_command("import", import_file=self.filepath)

        forms = Form.objects.all()
        self.assertEqual(forms.count(), 2)
        self.assertNotEqual(forms.last().pk, form_pk)
        self.assertNotEqual(forms.last().uuid, str(form.uuid))
        self.assertEqual(forms.last().active, False)
        self.assertEqual(forms.last().registration_backend, form.registration_backend)
        self.assertEqual(
            forms.last().registration_backend_options, form.registration_backend_options
        )
        self.assertEqual(forms.last().name, form.name)
        self.assertIsNone(forms.last().product)
        self.assertEqual(forms.last().slug, old_form_slug)
        self.assertEqual(forms.last().authentication_backends, ["digid"])
        self.assertEqual(forms.last().payment_backend, "ogone-legacy")
        self.assertEqual(
            forms.last().payment_backend_options, {"merchant_id": merchant.id}
        )

        form_definitions = FormDefinition.objects.all()
        fd2 = form_definitions.last()
        self.assertEqual(form_definitions.count(), 2)
        self.assertNotEqual(fd2.pk, form_definition_pk)
        self.assertNotEqual(fd2.uuid, str(form_definition.uuid))
        self.assertEqual(fd2.configuration, form_definition.configuration)
        self.assertEqual(fd2.login_required, form_definition.login_required)
        self.assertEqual(fd2.name, form_definition.name)
        self.assertEqual(fd2.slug, old_form_definition_slug)

        form_steps = FormStep.objects.all().order_by("pk")
        fs2 = form_steps.last()
        self.assertEqual(form_steps.count(), 2)
        self.assertNotEqual(fs2.pk, form_step_pk)
        self.assertNotEqual(fs2.uuid, str(form_step.uuid))
        self.assertEqual(fs2.form.pk, forms.last().pk)
        self.assertEqual(fs2.form_definition.pk, fd2.pk)
        self.assertEqual(fs2.optional, form_step.optional)
        self.assertEqual(fs2.order, form_step.order)

        form_logics = FormLogic.objects.all()
        self.assertEqual(2, form_logics.count())
        form_logic_2 = form_logics.last()
        self.assertNotEqual(form_logic_2.pk, form_logic_pk)
        self.assertNotEqual(form_logic_2.uuid, str(form_logic.uuid))
        self.assertEqual(form_logic_2.form.pk, forms.last().pk)

    def test_import_no_backends(self):
        """
        explicitly test import/export of Form without backends as they use custom fields/choices
        """
        product = ProductFactory.create()
        form = FormFactory.create(product=product)
        form_definition = FormDefinitionFactory.create()
        FormStepFactory.create(form=form, form_definition=form_definition)

        call_command("export", form.pk, self.filepath)

        form_definition.slug = "modified"
        form_definition.save()
        form.slug = "modified"
        form.save()

        call_command("import", import_file=self.filepath)

    def test_import_form_slug_already_exists(self):
        product = ProductFactory.create()
        form = FormFactory.create(product=product, slug="my-slug")
        form_definition = FormDefinitionFactory.create(
            configuration={"components": [{"key": "test-key", "type": "textfield"}]}
        )
        FormStepFactory.create(form=form, form_definition=form_definition)
        FormLogicFactory.create(form=form)

        call_command("export", form.pk, self.filepath)

        call_command("import", import_file=self.filepath)

        imported_form = Form.objects.last()
        imported_form_step = imported_form.formstep_set.first()
        imported_form_definition = imported_form_step.form_definition

        # check we imported a new form
        self.assertNotEqual(form.pk, imported_form.pk)
        # check we added random hex chars
        self.assertRegex(imported_form.slug, r"^my-slug-[0-9a-f]{6}$")
        # check uuid mapping still works
        self.assertEqual(imported_form_definition.uuid, form_definition.uuid)

    def test_import_form_definition_slug_already_exists_configuration_duplicate(self):
        product = ProductFactory.create()
        form = FormFactory.create(product=product)
        form_definition = FormDefinitionFactory.create(
            configuration={"components": [{"key": "test-key", "type": "textfield"}]}
        )
        form_step = FormStepFactory.create(form=form, form_definition=form_definition)
        form_logic = FormLogicFactory.create(form=form)

        form_pk, form_definition_pk, form_step_pk, form_logic_pk = (
            form.pk,
            form_definition.pk,
            form_step.pk,
            form_logic.pk,
        )

        call_command("export", form.pk, self.filepath)

        old_form_slug = form.slug
        form.slug = "modified"
        form.save()

        call_command("import", import_file=self.filepath)

        forms = Form.objects.all()
        self.assertEqual(forms.count(), 2)
        self.assertNotEqual(forms.last().pk, form_pk)
        self.assertNotEqual(forms.last().uuid, form.uuid)
        self.assertEqual(forms.last().active, False)
        self.assertEqual(forms.last().registration_backend, form.registration_backend)
        self.assertEqual(forms.last().name, form.name)
        self.assertEqual(forms.last().internal_name, form.internal_name)
        self.assertIsNone(forms.last().product)
        self.assertEqual(forms.last().slug, old_form_slug)

        form_definitions = FormDefinition.objects.all()
        fd2 = form_definitions.last()
        self.assertEqual(form_definitions.count(), 1)
        self.assertEqual(fd2.pk, form_definition_pk)
        self.assertEqual(fd2.uuid, form_definition.uuid)
        self.assertEqual(fd2.configuration, form_definition.configuration)
        self.assertEqual(fd2.login_required, form_definition.login_required)
        self.assertEqual(fd2.name, form_definition.name)
        self.assertEqual(fd2.internal_name, form_definition.internal_name)
        self.assertEqual(fd2.slug, form_definition.slug)

        form_steps = FormStep.objects.all().order_by("pk")
        fs2 = form_steps.last()
        self.assertEqual(form_steps.count(), 2)
        self.assertNotEqual(fs2.pk, form_step_pk)
        self.assertNotEqual(fs2.uuid, form_step.uuid)
        self.assertEqual(fs2.form.pk, forms.last().pk)
        self.assertEqual(fs2.form_definition.pk, fd2.pk)
        self.assertEqual(fs2.optional, form_step.optional)
        self.assertEqual(fs2.order, form_step.order)

        form_logics = FormLogic.objects.all()
        form_logic_2 = form_logics.last()
        self.assertEqual(form_logics.count(), 2)
        self.assertNotEqual(form_logic_2.pk, form_logic_pk)
        self.assertEqual(forms.last().pk, form_logic_2.form.pk)

    def test_import_form_definition_slug_already_exists_configuration_different(self):
        product = ProductFactory.create()
        form = FormFactory.create(product=product)
        form_definition = FormDefinitionFactory.create(
            configuration={"components": [{"key": "test-key", "type": "textfield"}]}
        )
        form_step = FormStepFactory.create(form=form, form_definition=form_definition)
        form_logic = FormLogicFactory.create(form=form)

        form_pk, form_definition_pk, form_step_pk, form_logic_pk = (
            form.pk,
            form_definition.pk,
            form_step.pk,
            form_logic.pk,
        )

        call_command("export", form.pk, self.filepath)

        old_form_slug = form.slug
        form.slug = "modified"
        form.save()

        old_fd_config = form_definition.configuration
        form_definition.configuration = {"foo": ["bar"]}
        form_definition.save()

        call_command("import", import_file=self.filepath)

        forms = Form.objects.all()
        self.assertEqual(forms.count(), 2)
        self.assertNotEqual(forms.last().pk, form_pk)
        self.assertNotEqual(forms.last().uuid, form.uuid)
        self.assertEqual(forms.last().active, False)
        self.assertEqual(forms.last().registration_backend, form.registration_backend)
        self.assertEqual(forms.last().name, form.name)
        self.assertEqual(forms.last().internal_name, form.internal_name)
        self.assertIsNone(forms.last().product)
        self.assertEqual(forms.last().slug, old_form_slug)

        form_definitions = FormDefinition.objects.all()
        fd2 = form_definitions.last()
        self.assertEqual(form_definitions.count(), 2)
        self.assertNotEqual(fd2.pk, form_definition_pk)
        self.assertNotEqual(fd2.uuid, form_definition.uuid)
        self.assertEqual(fd2.configuration, old_fd_config)
        self.assertEqual(fd2.login_required, form_definition.login_required)
        self.assertEqual(fd2.name, form_definition.name)
        self.assertEqual(fd2.internal_name, form_definition.internal_name)
        self.assertEqual(fd2.slug, f"{form_definition.slug}-2")

        form_steps = FormStep.objects.all().order_by("pk")
        fs2 = form_steps.last()
        self.assertEqual(form_steps.count(), 2)
        self.assertNotEqual(fs2.pk, form_step_pk)
        self.assertNotEqual(fs2.uuid, form_step.uuid)
        self.assertEqual(fs2.form.pk, forms.last().pk)
        self.assertEqual(fs2.form_definition.pk, fd2.pk)
        self.assertEqual(fs2.optional, form_step.optional)
        self.assertEqual(fs2.order, form_step.order)

        form_logics = FormLogic.objects.all()
        form_logic_2 = form_logics.last()
        self.assertEqual(form_logics.count(), 2)
        self.assertNotEqual(form_logic_2.pk, form_logic_pk)
        self.assertEqual(forms.last().pk, form_logic_2.form.pk)
