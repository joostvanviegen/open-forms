from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class IrmaApp(AppConfig):
    name = "openforms.prefill.contrib.irma"
    label = "prefill_irma"
    verbose_name = _("Irma prefill plugin")

    def ready(self):
        # register the plugin
        from . import plugin  # noqa
