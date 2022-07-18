from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


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
    
    #def __str__(self):
    #    return force_str(self._meta.verbose_name)

    @property
    def service(self):
        s = self._service
        return s