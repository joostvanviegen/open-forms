"""
Test the render component node implementations for the built-in Formio component types.

These can be considered integration tests for the Formio aspect, relying on the out
of the box configuration in Open Forms through the registry.
"""
from django.test import TestCase, override_settings

from openforms.forms.tests.factories import FormFactory
from openforms.submissions.rendering import Renderer, RenderModes
from openforms.submissions.tests.factories import (
    SubmissionFactory,
    SubmissionFileAttachmentFactory,
    SubmissionStepFactory,
)

from ..nodes import ComponentNode


class FormNodeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        form = FormFactory.create(
            name="public name",
            internal_name="internal name",
            generate_minimal_setup=True,
            formstep__form_definition__configuration={
                "components": [
                    # container: visible fieldset without visible children
                    {
                        "type": "fieldset",
                        "label": "A container without visible children",
                        "hidden": False,
                        "components": [
                            {
                                "type": "textfield",
                                "key": "input1",
                                "label": "Input 1",
                                "hidden": True,
                            }
                        ],
                    },
                    # container: visible fieldset with visible children
                    {
                        "type": "fieldset",
                        "label": "A container with visible children",
                        "hidden": False,
                        "components": [
                            {
                                "type": "textfield",
                                "key": "input2",
                                "label": "Input 2",
                                "hidden": True,
                            },
                            {
                                "type": "textfield",
                                "key": "input3",
                                "label": "Input 3",
                                "hidden": False,
                            },
                        ],
                    },
                    # container: hidden fieldset with 'visible' children
                    {
                        "type": "fieldset",
                        "label": "A hidden container with visible children",
                        "hidden": True,
                        "components": [
                            {
                                "type": "textfield",
                                "key": "input4",
                                "label": "Input 4",
                                "hidden": False,
                            }
                        ],
                    },
                    # container: visible columns without visible children
                    {
                        "type": "columns",
                        "key": "columns1",
                        "label": "Columns 1",
                        "hidden": False,
                        "columns": [
                            {
                                "size": 6,
                                "components": [
                                    {
                                        "type": "textfield",
                                        "key": "input5",
                                        "label": "Input 5",
                                        "hidden": True,
                                    }
                                ],
                            },
                            {
                                "size": 6,
                                "components": [
                                    {
                                        "type": "textfield",
                                        "key": "input6",
                                        "label": "Input 6",
                                        "hidden": True,
                                    }
                                ],
                            },
                        ],
                    },
                    # container: visible columns with visible children
                    {
                        "type": "columns",
                        "key": "columns2",
                        "label": "Columns 2",
                        "hidden": False,
                        "columns": [
                            {
                                "size": 6,
                                "components": [
                                    {
                                        "type": "textfield",
                                        "key": "input7",
                                        "label": "Input 7",
                                        "hidden": False,
                                    }
                                ],
                            },
                            {
                                "size": 6,
                                "components": [
                                    {
                                        "type": "textfield",
                                        "key": "input8",
                                        "label": "Input 8",
                                        "hidden": True,
                                    }
                                ],
                            },
                        ],
                    },
                    # container: hidden columns with visible children
                    {
                        "type": "columns",
                        "key": "columns3",
                        "label": "Columns 3",
                        "hidden": True,
                        "columns": [
                            {
                                "size": 6,
                                "components": [
                                    {
                                        "type": "textfield",
                                        "key": "input9",
                                        "label": "Input 9",
                                        "hidden": False,
                                    }
                                ],
                            },
                            {
                                "size": 6,
                                "components": [
                                    {
                                        "type": "textfield",
                                        "key": "input10",
                                        "label": "Input 10",
                                        "hidden": True,
                                    }
                                ],
                            },
                        ],
                    },
                ]
            },
        )

        submission = SubmissionFactory.create(form=form)
        step = SubmissionStepFactory.create(
            submission=submission,
            form_step=form.formstep_set.get(),
            data={
                "input1": "aaaaa",
                "input2": "bbbbb",
                "input3": "ccccc",
                "input4": "ddddd",
                "input6": "fffff",
                "input7": "ggggg",
                "input8": "hhhhh",
                "input9": "iiiii",
                "input10": "jjjjj",
            },
        )

        # expose test data to test methods
        cls.submission = submission
        cls.step = step

    def test_fieldsets_hidden_if_all_children_hidden(self):
        # we always need a renderer instance
        renderer = Renderer(self.submission, mode=RenderModes.pdf, as_html=False)
        component = self.step.form_step.form_definition.configuration["components"][0]
        assert component["type"] == "fieldset"

        component_node = ComponentNode.build_node(
            step=self.step, component=component, renderer=renderer
        )

        self.assertFalse(component_node.is_visible)
        self.assertEqual(list(component_node), [])

    def test_fieldsets_visible_if_any_child_visible(self):
        # we always need a renderer instance
        renderer = Renderer(self.submission, mode=RenderModes.pdf, as_html=False)
        component = self.step.form_step.form_definition.configuration["components"][1]
        assert component["type"] == "fieldset"

        component_node = ComponentNode.build_node(
            step=self.step, component=component, renderer=renderer
        )

        self.assertTrue(component_node.is_visible)
        nodelist = list(component_node)
        self.assertEqual(len(nodelist), 2)
        self.assertEqual(nodelist[0].label, "A container with visible children")
        self.assertEqual(nodelist[1].label, "Input 3")

    def test_fieldset_hidden_if_marked_as_such_and_visible_children(self):
        # we always need a renderer instance
        renderer = Renderer(self.submission, mode=RenderModes.pdf, as_html=False)
        component = self.step.form_step.form_definition.configuration["components"][2]
        assert component["type"] == "fieldset"

        component_node = ComponentNode.build_node(
            step=self.step, component=component, renderer=renderer
        )

        self.assertFalse(component_node.is_visible)
        self.assertEqual(list(component_node), [])

    def test_fieldset_with_hidden_label(self):
        # we always need a renderer instance
        renderer = Renderer(self.submission, mode=RenderModes.pdf, as_html=False)
        component = {
            "type": "fieldset",
            "key": "fieldset",
            "label": "A hidden label",
            "hidden": False,
            "hideHeader": True,
        }

        component_node = ComponentNode.build_node(
            step=self.step, component=component, renderer=renderer
        )

        self.assertEqual(component_node.label, "")

    def test_columns_hidden_if_all_children_hidden(self):
        # we always need a renderer instance
        renderer = Renderer(self.submission, mode=RenderModes.pdf, as_html=False)
        component = self.step.form_step.form_definition.configuration["components"][3]
        assert component["type"] == "columns"

        component_node = ComponentNode.build_node(
            step=self.step, component=component, renderer=renderer
        )

        self.assertFalse(component_node.is_visible)
        self.assertEqual(list(component_node), [])

    def test_columns_visible_if_any_child_visible(self):
        # we always need a renderer instance
        renderer = Renderer(self.submission, mode=RenderModes.pdf, as_html=False)
        component = self.step.form_step.form_definition.configuration["components"][4]
        assert component["type"] == "columns"

        component_node = ComponentNode.build_node(
            step=self.step, component=component, renderer=renderer
        )

        self.assertTrue(component_node.is_visible)
        nodelist = list(component_node)
        self.assertEqual(len(nodelist), 2)
        self.assertEqual(nodelist[0].component["label"], "Columns 2")
        self.assertEqual(nodelist[1].label, "Input 7")

    def test_column_hidden_if_marked_as_such_and_visible_children(self):
        # we always need a renderer instance
        renderer = Renderer(self.submission, mode=RenderModes.pdf, as_html=False)
        component = self.step.form_step.form_definition.configuration["components"][5]
        assert component["type"] == "columns"

        component_node = ComponentNode.build_node(
            step=self.step, component=component, renderer=renderer
        )

        self.assertFalse(component_node.is_visible)
        self.assertEqual(list(component_node), [])

    def test_columns_never_output_label(self):
        component = self.step.form_step.form_definition.configuration["components"][5]
        assert component["type"] == "columns"

        for render_mode in RenderModes.values:
            with self.subTest(render_mode=render_mode):
                renderer = Renderer(self.submission, mode=render_mode, as_html=False)

                component_node = ComponentNode.build_node(
                    step=self.step, component=component, renderer=renderer
                )

                self.assertEqual(component_node.label, "")
                self.assertIsNone(component_node.value)

    def test_wysiwyg_component(self):
        """
        WYSIWYG is only displayed in confirmation PDF and CLI rendering.
        """
        component = {
            "type": "content",
            "key": "content",
            "html": "<p>WYSIWYG with <strong>markup</strong></p>",
            "input": False,
            "label": "Content",
            "hidden": False,
        }
        submission = SubmissionFactory.create(
            form__name="public name",
            form__generate_minimal_setup=True,
            form__formstep__form_definition__configuration={"components": [component]},
        )
        step = SubmissionStepFactory.create(
            submission=submission,
            form_step=submission.form.formstep_set.get(),
        )
        expected_visibility = {
            RenderModes.confirmation_email: False,
            RenderModes.pdf: True,
            RenderModes.cli: True,
        }

        for render_mode, is_visible in expected_visibility.items():
            with self.subTest(render_mode=render_mode):
                renderer = Renderer(submission, mode=render_mode, as_html=False)
                component_node = ComponentNode.build_node(
                    step=step, component=component, renderer=renderer
                )

                self.assertEqual(component_node.is_visible, is_visible)

        with self.subTest(as_html=True):
            renderer = Renderer(submission, mode=RenderModes.pdf, as_html=True)
            component_node = ComponentNode.build_node(
                step=step, component=component, renderer=renderer
            )

            self.assertEqual(
                component_node.value, "<p>WYSIWYG with <strong>markup</strong></p>"
            )

        with self.subTest(as_html=False):
            renderer = Renderer(submission, mode=RenderModes.pdf, as_html=False)
            component_node = ComponentNode.build_node(
                step=step, component=component, renderer=renderer
            )

            self.assertEqual(component_node.value, "WYSIWYG with markup")

    @override_settings(BASE_URL="http://localhost:8000")
    def test_file_component_email_registration(self):
        component = {
            "type": "file",
            "key": "file",
            "label": "My File",
            "hidden": False,
        }
        submission = SubmissionFactory.create(
            form__name="public name",
            form__generate_minimal_setup=True,
            form__formstep__form_definition__configuration={"components": [component]},
        )

        step = SubmissionStepFactory.create(
            submission=submission,
            form_step=submission.form.formstep_set.get(),
            data={
                "file": [
                    {
                        "data": {
                            "baseUrl": "http://localhost:8000/api/v1/",
                            "form": "",
                            "name": "blank.doc",
                            "project": "",
                            "size": 1048576,
                            "url": "http://localhost:8000/api/v1/submissions/files/35527900-8248-4e75-a553-c2d1039a002b",
                        },
                        "name": "blank-65faf10b-afaf-48af-a749-ff5780abf75b.doc",
                        "originalName": "blank.doc",
                        "size": 1048576,
                        "storage": "url",
                        "type": "application/msword",
                        "url": "http://localhost:8000/api/v1/submissions/files/35527900-8248-4e75-a553-c2d1039a002b",
                    }
                ]
            },
        )
        SubmissionFileAttachmentFactory.create(
            submission_step=step,
            form_key="file",
            file_name="blank-renamed.doc",
            original_name="blank.doc",
        )

        with self.subTest(as_html=True):
            renderer = Renderer(submission, mode=RenderModes.registration, as_html=True)
            component_node = ComponentNode.build_node(
                step=step, component=component, renderer=renderer
            )

            link = component_node.render()
            self.assertTrue(link.startswith('My File: <a href="http://localhost:8000/'))
            self.assertTrue(
                link.endswith(
                    '" target="_blank" rel="noopener noreferrer">blank-renamed.doc</a>'
                )
            )

        with self.subTest(as_html=False):
            renderer = Renderer(
                submission, mode=RenderModes.registration, as_html=False
            )
            component_node = ComponentNode.build_node(
                step=step, component=component, renderer=renderer
            )
            link = component_node.render()
            self.assertTrue(link.startswith("My File: http://localhost:8000/"))
            self.assertTrue(link.endswith(" (blank-renamed.doc)"))

    def test_file_component_email_registration_no_file(self):
        # via GH issue #1594
        component = {
            "type": "file",
            "key": "file",
            "label": "My File",
            "hidden": False,
        }
        submission = SubmissionFactory.create(
            form__name="public name",
            form__generate_minimal_setup=True,
            form__formstep__form_definition__configuration={"components": [component]},
        )
        step = SubmissionStepFactory.create(
            submission=submission,
            form_step=submission.form.formstep_set.get(),
            data={},
        )
        renderer = Renderer(submission, mode=RenderModes.registration, as_html=True)
        component_node = ComponentNode.build_node(
            step=step, component=component, renderer=renderer
        )
        link = component_node.render()
        self.assertEqual(link, "My File: ")
