from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes

from .client import IrmaClient


class IrmaConfigManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("_service")

class IrmaConfig(SingletonModel):

    _service = models.OneToOneField(
        "zgw_consumers.Service",
        verbose_name=_("Irma API"),
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type" : APITypes.orc},
        null=True,
    )

    objects = IrmaConfigManager()

    class Meta:
        verbose_name = _("Irma configuration")
    
    def __str__(self):
        return force_str(self._meta.verbose_name)

    def get_client(self) -> IrmaClient:
        if not self.irma_service:
            raise RuntimeError("You must configure an Irma service!")

        default_client = self.irma_service.build_client()
        irma_client = IrmaClient(
            service=default_client.service,
            base_path=default_client.base_path,
        )
        irma_client.auth_value = default_client.auth_header
        return irma_client