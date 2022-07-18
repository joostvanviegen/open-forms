from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.translation import ugettext as _

from ..models import Form, FormDefinition, FormStep
from .factories import (
    FormDefinitionFactory,
    FormFactory,
    FormLogicFactory,
    FormStepFactory,
)


class FormTestCase(TestCase):
    def setUp(self) -> None:
        self.form = FormFactory.create()
        self.form_def_1 = FormDefinitionFactory.create()
        self.form_def_2 = FormDefinitionFactory.create()
        self.form_step_1 = FormStepFactory.create(
            form=self.form, form_definition=self.form_def_1
        )
        self.form_step_2 = FormStepFactory.create(
            form=self.form, form_definition=self.form_def_2
        )

    def test_str(self):
        form = FormFactory.create(name="my-form")
        self.assertEqual(str(form), "my-form")

        form.internal_name = "internal"
        self.assertEqual(str(form), "internal")

        form._is_deleted = True
        self.assertEqual(
            str(form), _("{name} (deleted)").format(name=form.internal_name)
        )

    def test_login_required(self):
        self.assertFalse(self.form.login_required)
        self.form_def_2.login_required = True
        self.form_def_2.save()
        self.assertTrue(self.form.login_required)

    def test_copying_a_form(self):
        form1 = FormFactory.create(
            slug="a-form", name="A form", internal_name="A form internal"
        )

        form2 = form1.copy()
        form3 = form1.copy()

        self.assertEqual(form2.slug, _("{slug}-copy").format(slug=form1.slug))
        self.assertEqual(form2.name, _("{name} (copy)").format(name=form1.name))
        self.assertEqual(
            form2.internal_name, _("{name} (copy)").format(name=form1.internal_name)
        )
        self.assertEqual(form3.slug, f"{form2.slug}-2")
        self.assertEqual(form3.name, _("{name} (copy)").format(name=form1.name))
        self.assertEqual(
            form3.internal_name, _("{name} (copy)").format(name=form1.internal_name)
        )

    def test_get_keys_for_email_confirmation(self):
        form = FormFactory.create()

        def_1 = FormDefinitionFactory.create(
            configuration={
                "display": "form",
                "components": [
                    {
                        "key": "aaa",
                        "type": "textfield",
                        "label": "AAA",
                        "confirmationRecipient": True,
                    },
                ],
            }
        )
        def_2 = FormDefinitionFactory.create(
            configuration={
                "display": "form",
                "components": [
                    {
                        "key": "bbb",
                        "type": "textfield",
                        "label": "BBB",
                        "confirmationRecipient": True,
                        "multiple": True,
                    },
                ],
            }
        )
        FormStepFactory.create(form=form, form_definition=def_1)
        FormStepFactory.create(form=form, form_definition=def_2)

        actual = form.get_keys_for_email_confirmation()
        self.assertEqual(set(actual), {"aaa", "bbb"})

    def test_iter_components(self):
        form = FormFactory.create()

        def_1 = FormDefinitionFactory.create(
            configuration={
                "display": "form",
                "components": [
                    {
                        "key": "aaa",
                        "label": "AAA",
                        "type": "textfield",
                    },
                ],
            }
        )
        def_2 = FormDefinitionFactory.create(
            configuration={
                "display": "form",
                "components": [
                    {
                        "key": "bbb",
                        "label": "BBB",
                        "type": "textfield",
                        "multiple": True,
                        "components": [
                            {
                                "key": "ccc",
                                "type": "textfield",
                                "label": "CCC",
                                "multiple": True,
                            },
                        ],
                    },
                ],
            }
        )
        FormStepFactory.create(form=form, form_definition=def_1)
        FormStepFactory.create(form=form, form_definition=def_2)

        with self.subTest("recursive"):
            actual = list(form.iter_components(recursive=True))
            expected = [
                {
                    "key": "aaa",
                    "label": "AAA",
                    "type": "textfield",
                },
                {
                    "key": "bbb",
                    "type": "textfield",
                    "label": "BBB",
                    "multiple": True,
                    "components": [
                        {
                            "key": "ccc",
                            "type": "textfield",
                            "label": "CCC",
                            "multiple": True,
                        },
                    ],
                },
                {
                    "key": "ccc",
                    "label": "CCC",
                    "type": "textfield",
                    "multiple": True,
                },
            ]

            self.assertEqual(actual, expected)

        with self.subTest("non-recursive"):
            actual = list(form.iter_components(recursive=False))
            expected = [
                {
                    "key": "aaa",
                    "label": "AAA",
                    "type": "textfield",
                },
                {
                    "key": "bbb",
                    "type": "textfield",
                    "label": "BBB",
                    "multiple": True,
                    "components": [
                        {
                            "key": "ccc",
                            "type": "textfield",
                            "label": "CCC",
                            "multiple": True,
                        },
                    ],
                },
            ]

            self.assertEqual(actual, expected)

    def test_iter_components_ordering(self):
        # failing test for Github #750
        form = FormFactory.create()

        def_2 = FormDefinitionFactory.create(
            configuration={
                "display": "form",
                "components": [
                    {
                        "key": "bbb",
                        "label": "BBB",
                        "type": "textfield",
                    },
                ],
            }
        )
        def_1 = FormDefinitionFactory.create(
            configuration={
                "display": "form",
                "components": [
                    {
                        "key": "aaa",
                        "label": "AAA",
                        "type": "textfield",
                    },
                ],
            }
        )
        # create out of order so related queryset would sort bad
        step_2 = FormStepFactory.create(form=form, form_definition=def_2)
        step_1 = FormStepFactory.create(form=form, form_definition=def_1)
        # set correct expected order
        step_2.swap(step_1)

        # check we fixed the ordering of form steps
        actual = list(form.iter_components(recursive=True))
        expected = [
            {
                "key": "aaa",
                "label": "AAA",
                "type": "textfield",
            },
            {
                "key": "bbb",
                "label": "BBB",
                "type": "textfield",
            },
        ]

        self.assertEqual(actual, expected)


class FormQuerysetTestCase(TestCase):
    def test_queryset_live(self):
        FormFactory.create(active=True, deleted_=True)
        form2 = FormFactory.create(active=True)
        FormFactory.create(active=False, deleted_=True)
        FormFactory.create(active=False)

        active = list(Form.objects.live())
        self.assertEqual(active, [form2])


class FormDefinitionTestCase(TestCase):
    def setUp(self) -> None:
        self.form_definition = FormDefinitionFactory.create()

    def test_deleting_form_definition_fails_when_used_by_form(self):
        self.form_definition.delete()
        self.assertFalse(
            FormDefinition.objects.filter(pk=self.form_definition.pk).exists()
        )

        form = FormFactory.create()
        form_definition = FormDefinitionFactory.create()
        FormStepFactory.create(form=form, form_definition=form_definition)
        with self.assertRaises(ValidationError):
            form_definition.delete()
        self.assertTrue(FormDefinition.objects.filter(pk=form_definition.pk).exists())

    def test_copying_a_form_definition_makes_correct_copies(self):
        form_definition_1 = FormDefinitionFactory.create(
            slug="a-form-definition",
            name="A form definition",
            internal_name="A internal",
        )

        form_definition_2 = form_definition_1.copy()
        form_definition_3 = form_definition_1.copy()

        self.assertEqual(
            form_definition_2.slug, _("{slug}-copy").format(slug="a-form-definition")
        )
        self.assertEqual(
            form_definition_2.name, _("{name} (copy)").format(name="A form definition")
        )
        self.assertEqual(
            form_definition_2.internal_name,
            _("{name} (copy)").format(name="A internal"),
        )
        self.assertEqual(form_definition_3.slug, f"{form_definition_2.slug}-2")
        self.assertEqual(
            form_definition_3.name, _("{name} (copy)").format(name="A form definition")
        )
        self.assertEqual(
            form_definition_3.internal_name,
            _("{name} (copy)").format(name="A internal"),
        )

    def test_get_keys_for_email_confirmation(self):
        form_definition = FormDefinitionFactory.create(
            configuration={
                "display": "form",
                "components": [
                    {"key": "aaa", "label": "AAA", "confirmationRecipient": True},
                    {"key": "bbb", "label": "BBB", "confirmationRecipient": False},
                    {"key": "ccc", "label": "CCC", "confirmationRecipient": True},
                ],
            }
        )

        keys = form_definition.get_keys_for_email_confirmation()

        self.assertIn("aaa", keys)
        self.assertNotIn("bbb", keys)
        self.assertIn("ccc", keys)

    def test_form_definition_sensitive_information_returns_correct_fields(self):
        self.form_definition_with_sensitive_information = FormDefinitionFactory.create(
            configuration={
                "components": [
                    {"key": "textFieldSensitive", "isSensitiveData": True},
                    {"key": "textFieldNotSensitive", "isSensitiveData": False},
                ],
            }
        )
        self.assertEqual(self.form_definition.sensitive_fields, [])
        self.assertEqual(
            self.form_definition_with_sensitive_information.sensitive_fields,
            ["textFieldSensitive"],
        )


class FormStepTestCase(TestCase):
    def test_str(self):
        step = FormStepFactory.create(
            form__internal_name="InternalForm",
            form_definition__internal_name="InternalDef",
            order=1,
        )
        expected = _("{form_name} step {order}: {definition_name}").format(
            form_name=step.form.admin_name,
            order=step.order,
            definition_name=step.form_definition.admin_name,
        )
        self.assertEqual(str(step), expected)

    def test_str_no_relation(self):
        step = FormStep()
        self.assertEqual(str(step), "FormStep object (None)")


class FormLogicTests(TestCase):
    def test_block_form_logic_trigger_step_other_form(self):
        form1, form2 = FormFactory.create_batch(2)
        step = FormStepFactory.create(form=form1)
        other_step = FormStepFactory.create(form=form2)

        with self.subTest("Invalid configuration"):
            logic = FormLogicFactory.build(form=form1)
            logic.trigger_from_step = other_step
            with self.assertRaises(ValidationError):
                logic.clean()

        with self.subTest("Valid configuration"):
            logic = FormLogicFactory.build(form=form1)
            logic.trigger_from_step = step
            try:
                logic.clean()
            except ValidationError:
                self.fail("Should be allowed")

        with self.subTest("No trigger from step configured"):
            logic = FormLogicFactory.build(form=form1)
            try:
                logic.clean()
            except ValidationError:
                self.fail("Should be allowed")
