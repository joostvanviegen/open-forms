from mozilla_django_oidc.utils import import_from_settings

import openforms.authentication.contrib.digid_oidc.settings as app_settings

from .models import OpenIDConnectPublicConfig


# TODO allow model class to be set?
class SoloConfigMixin:
    @staticmethod
    def get_settings(attr, *args):
        if hasattr(app_settings, attr):
            return getattr(app_settings, attr)

        config = OpenIDConnectPublicConfig.get_solo()
        attr_lowercase = attr.lower()
        if getattr(config, attr_lowercase, ""):
            return getattr(config, attr_lowercase)
        return import_from_settings(attr, *args)