from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import APIException


class AppointmentException(Exception):
    pass


class AppointmentDeleteFailed(AppointmentException):
    pass


class AppointmentCreateFailed(AppointmentException):
    pass


class AppointmentInteractionFailed(AppointmentException):
    def __init__(self, *args, **kwargs):
        self.should_retry = kwargs.pop("should_retry", False)
        super().__init__(*args, **kwargs)


class AppointmentRegistrationFailed(AppointmentInteractionFailed):
    pass


class AppointmentUpdateFailed(AppointmentInteractionFailed):
    pass


class CancelAppointmentFailed(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = _("Unable to cancel appointment.")
    default_code = "cancel_appointment_failed"
