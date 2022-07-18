from pathlib import Path

from django.core.files import File

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from openforms.forms.tests.factories import FormFactory, FormStepFactory

from .factories import SubmissionFactory, TemporaryFileUploadFactory
from .mixins import SubmissionsMixin

TEST_FILES_DIR = Path(__file__).parent / "files"


@temp_private_root()
class SubmissionStepValidationTests(SubmissionsMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # ensure there is a form definition
        cls.form = FormFactory.create()
        cls.step1 = FormStepFactory.create(
            form=cls.form,
            form_definition__configuration={
                "components": [
                    {
                        "key": "test-key",
                        "type": "textfield",
                    },
                    {
                        "key": "my_file",
                        "type": "file",
                    },
                ]
            },
        )

        cls.form_url = reverse(
            "api:form-detail", kwargs={"uuid_or_slug": cls.form.uuid}
        )

        # ensure there is a submission
        cls.submission = SubmissionFactory.create(form=cls.form)

    def test_validate_bad_file_content_type(self):
        with open(TEST_FILES_DIR / "image-256x256.pdf", "rb") as infile:
            upload = TemporaryFileUploadFactory.create(
                file_name="my-pdf.pdf",
                content=File(infile),
                content_type="application/pdf",
            )
        data = {
            "test-key": "foo",
            "my_file": [
                {
                    "url": f"http://server/api/v1/submissions/files/{upload.uuid}",
                    "data": {
                        "url": f"http://server/api/v1/submissions/files/{upload.uuid}",
                        "form": "",
                        "name": "my-pdf.pdf",
                        "size": 585,
                        "baseUrl": "http://server",
                        "project": "",
                    },
                    "name": "my-pdf-12305610-2da4-4694-a341-ccb919c3d543.png",
                    "size": 585,
                    "type": "application/pdf",  # we are lying!
                    "storage": "url",
                    "originalName": "my-pdf.pdf",
                },
            ],
        }
        self._add_submission_to_session(self.submission)
        endpoint = reverse(
            "api:submission-steps-validate",
            kwargs={
                "submission_uuid": self.submission.uuid,
                "step_uuid": self.step1.uuid,
            },
        )

        response = self.client.post(endpoint, {"data": data})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_fields = [param["name"] for param in response.json()["invalidParams"]]
        self.assertEqual(error_fields, ["data.my_file"])
