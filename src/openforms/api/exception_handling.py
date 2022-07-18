import logging
import uuid
from collections import OrderedDict
from typing import List, Union

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse

from rest_framework import exceptions

from .serializers import ExceptionSerializer, ValidationErrorSerializer
from .utils import underscore_to_camel

logger = logging.getLogger(__name__)

ErrorSerializer = Union[ExceptionSerializer, ValidationErrorSerializer]


def _translate_exceptions(exc):
    # Taken from DRF default exc handler
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    return exc


# TODO: see if we can re-use openforms.submissions.parsers.IgnoreDataJSONRenderer for
# the camelize keys skipping?
#
# We are ignoring the 'data' key in snake -> camel case conversion. This is the key
# that's used to submit formio data to the backend, which contains sub-keys set by
# end-users and can't be automatically converted. Consequently, error messages for
# those sub-keys should not be transformed.
def get_validation_errors(validation_errors: Union[dict, list], camelize=True):
    if isinstance(validation_errors, list):
        for i, item in enumerate(validation_errors):
            for err in get_validation_errors(item):
                err["name"] = f"{i}.{err['name']}"
                yield err
    else:
        for field_name, error_list in validation_errors.items():
            new_name = underscore_to_camel(field_name) if camelize else field_name

            # nested validation for fields where many=True
            if isinstance(error_list, list):
                for i, nested_error_dict in enumerate(error_list):
                    if isinstance(nested_error_dict, dict):
                        for err in get_validation_errors(
                            nested_error_dict, camelize=field_name != "data"
                        ):
                            err["name"] = f"{new_name}.{i}.{err['name']}"
                            yield err

            # nested validation - recursively call the function
            if isinstance(error_list, dict):
                for err in get_validation_errors(
                    error_list, camelize=field_name != "data"
                ):
                    err["name"] = f"{new_name}.{err['name']}"
                    yield err
                continue

            if isinstance(error_list, exceptions.ErrorDetail):
                error_list = [error_list]

            for error in error_list:
                if isinstance(error, dict):
                    continue

                if isinstance(error, list):
                    for err in error:
                        yield OrderedDict(
                            [
                                # see https://tools.ietf.org/html/rfc7807#section-3.1
                                # ('type', 'about:blank'),
                                (
                                    "name",
                                    underscore_to_camel(field_name)
                                    if camelize
                                    else field_name,
                                ),
                                ("code", err.code),
                                ("reason", str(err)),
                            ]
                        )
                else:
                    yield OrderedDict(
                        [
                            # see https://tools.ietf.org/html/rfc7807#section-3.1
                            # ('type', 'about:blank'),
                            (
                                "name",
                                underscore_to_camel(field_name)
                                if camelize
                                else field_name,
                            ),
                            ("code", error.code),
                            ("reason", str(error)),
                        ]
                    )


class HandledException:
    def __init__(self, exc: exceptions.APIException, response, request=None):
        self.exc = exc
        assert 400 <= response.status_code < 600, "Unsupported status code"
        self.response = response
        self.request = request
        self._exc_id = str(uuid.uuid4())

    @property
    def _error_detail(self) -> str:
        if isinstance(self.exc, exceptions.ValidationError):
            # ErrorDetail from DRF is a str subclass
            data = getattr(self.response, "data", {})
            if isinstance(data, list):
                return ""
            return data.get("detail", "")
        # any other exception -> return the raw ErrorDetails object so we get
        # access to the code later
        return self.exc.detail

    @classmethod
    def as_serializer(
        cls, exc: exceptions.APIException, response, request=None
    ) -> ErrorSerializer:
        """
        Return the appropriate serializer class instance.
        """
        exc = _translate_exceptions(exc)
        self = cls(exc, response, request)
        self.log()

        if isinstance(exc, exceptions.ValidationError):
            serializer_class = ValidationErrorSerializer
        else:
            serializer_class = ExceptionSerializer

        return serializer_class(instance=self)

    def log(self):
        logger.exception("Exception %s ocurred", self._exc_id)

    @property
    def type(self) -> str:
        exc_detail_url = reverse(
            "error-detail",
            kwargs={"exception_class": self.exc.__class__.__name__},
        )
        if self.request is not None:
            exc_detail_url = self.request.build_absolute_uri(exc_detail_url)
        return exc_detail_url

    @property
    def code(self) -> str:
        if isinstance(self.exc, exceptions.ValidationError):
            return self.exc.default_code
        return self._error_detail.code if self._error_detail else ""

    @property
    def title(self) -> str:
        """
        Return the generic message for this type of exception.
        """
        return getattr(self.exc, "default_detail", str(self._error_detail))

    @property
    def status(self) -> int:
        return self.response.status_code

    @property
    def detail(self) -> str:
        return str(self._error_detail)

    @property
    def instance(self) -> str:
        return f"urn:uuid:{self._exc_id}"

    @property
    def invalid_params(self) -> Union[None, List]:
        return [error for error in get_validation_errors(self.exc.detail)]
