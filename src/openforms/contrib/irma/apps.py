from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class IrmaApp(AppConfig):
    name = "openforms.contrib.irma"
    label = "irma"
    verbose_name = "Irma code & configuration"

    def ready(self):
        # register the plugin
        from . import irma_main  # noqa
