from django.db import models
from django.utils.translation import gettext_lazy as __name__

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes

class IrmaConfigManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("service")

class IrmaConfig(SingletonModel):
    service = models.OneToOneField(
        "zgw_consumers.Service",
        verbose_name =_("Irma API"),
        on_delete=models.PROTECT,
        limit_choices_to={"api_type": APITypes.orc},
        related_name="+",
        null=True,
    )

    objects = IrmaConfigManager()

    class Meta:
        verbose_name = _("Irma configuration")