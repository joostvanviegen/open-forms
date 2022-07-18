import logging
import os.path
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Iterator, Optional, Tuple
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.temp import NamedTemporaryFile
from django.urls import Resolver404, resolve
from django.utils.translation import gettext as _

import magic
import PIL
from glom import glom
from PIL import Image
from rest_framework.exceptions import ErrorDetail, ValidationError

from openforms.api.exceptions import RequestEntityTooLarge
from openforms.conf.utils import Filesize
from openforms.formio.service import mimetype_allowed
from openforms.formio.typing import Component
from openforms.submissions.models import (
    Submission,
    SubmissionFileAttachment,
    SubmissionStep,
    TemporaryFileUpload,
)

logger = logging.getLogger(__name__)

DEFAULT_IMAGE_MAX_SIZE = (10000, 10000)

# validate the size as Formio does (client-side) - meaning 1MB is actually 1MiB
# https://github.com/formio/formio.js/blob/4.12.x/src/components/file/File.js#L523
file_size_cast = Filesize(system=Filesize.S_BINARY)


def temporary_upload_uuid_from_url(url: str) -> Optional[str]:
    try:
        match = resolve(urlparse(url)[2])
    except Resolver404:
        return None
    else:
        if match.view_name == "api:submissions:temporary-file":
            return str(match.kwargs["uuid"])
        else:
            return None


def temporary_upload_from_url(url: str) -> Optional[TemporaryFileUpload]:
    uuid = temporary_upload_uuid_from_url(url)
    if not uuid:
        return None
    try:
        return TemporaryFileUpload.objects.get(uuid=uuid)
    except TemporaryFileUpload.DoesNotExist:
        return None


def clean_mime_type(mimetype: str) -> str:
    # cleanup a user supplied mime-type against injection attacks
    m = re.match(r"^[a-z0-9\.+-]+\/[a-z0-9\.+-]+", mimetype)
    if not m:
        return "application/octet-stream"
    else:
        return m.group()


def append_file_num_postfix(
    original_name: str, new_name: str, num: int, max: int
) -> str:
    if not new_name:
        return ""

    _, ext = os.path.splitext(original_name)
    new_name, _ = os.path.splitext(new_name)
    if max <= 1:
        postfix = ""
    else:
        digits = len(str(max))
        postfix = f"-{num:0{digits}}"
    return f"{new_name}{postfix}{ext}"


@dataclass
class UploadContext:
    upload: TemporaryFileUpload
    component: Component
    index: int  # one-based
    form_key: str  # formio key
    num_uploads: int


def iter_step_uploads(
    submission_step: SubmissionStep, data=None
) -> Iterator[UploadContext]:
    """
    Iterate over all the uploads for a given submission step.

    Yield every uploaded file and its context within the form step for further
    processing.
    """
    data = data or submission_step.data
    components = list(submission_step.form_step.iter_components(recursive=True))
    uploads = resolve_uploads_from_data(components, data)
    for key, (component, upload_instances) in uploads.items():
        # formio sends a list of uploads even with multiple=False
        for i, upload in enumerate(upload_instances, start=1):
            yield UploadContext(
                upload=upload,
                form_key=key,
                component=component,
                index=i,
                num_uploads=len(upload_instances),
            )


def validate_uploads(submission_step: SubmissionStep, data: Optional[dict]) -> None:
    """
    Validate the file uploads in the submission step data.

    File uploads are stored in a temporary file uploads table and the references to them
    are included in the step submission data. This function validates that the actual
    content and metadata of files conforms to the configured file upload components.
    """
    validation_errors = defaultdict(list)
    for upload_context in iter_step_uploads(submission_step, data=data):
        upload, component, key = (
            upload_context.upload,
            upload_context.component,
            upload_context.form_key,
        )
        allowed_mime_types = glom(component, "file.type", default=[])

        # perform content type validation
        with upload.content.open("rb") as infile:
            # 2048 bytes per recommendation of python-magic
            file_mime_type = magic.from_buffer(infile.read(2048), mime=True)

        invalid_file_type_error = ErrorDetail(
            _("The file '{filename}' is not a valid file type.").format(
                filename=upload.file_name
            ),
            code="invalid",
        )

        if upload.content_type != file_mime_type:
            validation_errors[key].append(invalid_file_type_error)
            continue

        # validate that the mime type passes the allowlist
        if not mimetype_allowed(file_mime_type, allowed_mime_types):
            logger.warning(
                "Blocking submission upload %d because of invalid mime type check",
                upload.id,
            )
            validation_errors[key].append(invalid_file_type_error)
            continue

    if validation_errors:
        raise ValidationError(validation_errors)


def attach_uploads_to_submission_step(submission_step: SubmissionStep) -> list:
    # circular import
    from .tasks import resize_submission_attachment

    result = list()

    for upload_context in iter_step_uploads(submission_step):
        upload, component, key = (
            upload_context.upload,
            upload_context.component,
            upload_context.form_key,
        )

        # grab resize settings
        resize_apply = glom(component, "of.image.resize.apply", default=False)
        resize_size = (
            glom(component, "of.image.resize.width", default=DEFAULT_IMAGE_MAX_SIZE[0]),
            glom(
                component, "of.image.resize.height", default=DEFAULT_IMAGE_MAX_SIZE[1]
            ),
        )
        file_max_size = file_size_cast(
            glom(component, "fileMaxSize", default="") or settings.MAX_FILE_UPLOAD_SIZE
        )

        base_name = glom(component, "file.name", default="")

        if upload.file_size > file_max_size:
            raise RequestEntityTooLarge(
                _(
                    "Upload {uuid} exceeds the maximum upload size of {max_size}b"
                ).format(
                    uuid=upload.uuid,
                    max_size=file_max_size,
                ),
            )

        file_name = append_file_num_postfix(
            upload.file_name,
            base_name,
            upload_context.index,
            upload_context.num_uploads,
        )

        attachment, created = SubmissionFileAttachment.objects.create_from_upload(
            submission_step, key, upload, file_name=file_name
        )
        result.append((attachment, created))

        if created and resize_apply and resize_size:
            # NOTE there is a possible race-condition if user completes a submission before this resize task is done
            # see https://github.com/open-formulieren/open-forms/issues/507
            resize_submission_attachment.delay(attachment.id, resize_size)

    return result


def cleanup_submission_temporary_uploaded_files(submission: Submission):
    for attachment in SubmissionFileAttachment.objects.for_submission(
        submission
    ).filter(temporary_file__isnull=False):
        attachment.temporary_file.delete()


def cleanup_unclaimed_temporary_uploaded_files(age=timedelta(days=2)):
    for file in TemporaryFileUpload.objects.select_prune(age).filter(attachments=None):
        file.delete()


def iter_component_data(components: Iterable[dict], data: dict, filter_types=None):
    if not data or not components:
        return
    for component in components:
        key = component.get("key")
        type = component.get("type")
        if not key or not type:
            continue
        if key not in data:
            continue
        if filter_types and type not in filter_types:
            continue
        yield component, data[key]


def resolve_uploads_from_data(components: Iterable[dict], data: dict) -> dict:
    """
    "my_file": [
        {
            "url": "http://server/api/v1/submissions/files/62f2ec22-da7d-4385-b719-b8637c1cd483",
            "data": {
                "url": "http://server/api/v1/submissions/files/62f2ec22-da7d-4385-b719-b8637c1cd483",
                "form": "",
                "name": "my-image.jpg",
                "size": 46114,
                "baseUrl": "http://server/form",
                "project": "",
            },
            "name": "my-image-12305610-2da4-4694-a341-ccb919c3d543.jpg",
            "size": 46114,
            "type": "image/jpg",
            "storage": "url",
            "originalName": "my-image.jpg",
        }
    ]
    """
    result = dict()

    for component, upload_info in iter_component_data(
        components, data, filter_types={"file"}
    ):
        key = component["key"]
        uploads = list()
        for info in upload_info:
            # lets be careful with malformed user data
            if not isinstance(info, dict) or not isinstance(info.get("url"), str):
                continue

            upload = temporary_upload_from_url(info["url"])
            if upload:
                uploads.append(upload)

        if uploads:
            result[key] = (component, uploads)

    return result


def resize_attachment(
    attachment: SubmissionFileAttachment, size: Tuple[int, int]
) -> bool:
    """
    'safe' resize an attached image that might not be an image or not need resize at all
    """
    try:
        # this might not actually be an image file; let's open it and see
        image = Image.open(
            attachment.content,
            formats=(
                "png",
                "jpeg",
            ),
        )
    except PIL.UnidentifiedImageError:
        # oops
        return False
    except OSError:
        # more specific
        return False
    except ValueError:
        # more specific
        return False
    else:
        # check if we have work
        if image.width <= size[0] and image.height <= size[1]:
            return False

        # TODO SpooledTemporaryFile but what limit?
        with NamedTemporaryFile() as tmp:
            image.thumbnail(size)
            image.save(tmp, image.format)
            attachment.content.save(attachment.content.name, tmp, save=True)
            return True
