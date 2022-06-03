from typing import Any, Dict, Optional

from django.http import HttpRequest, HttpResponseBadRequest, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

import requests
from furl import furl
from rest_framework.reverse import reverse

from digid_eherkenning_oidc_generics.models import (
    OpenIDConnectDigiDMachtigenConfig,
    OpenIDConnectEHerkenningBewindvoeringConfig,
    OpenIDConnectEHerkenningConfig,
    OpenIDConnectPublicConfig,
)
from openforms.contrib.digid_eherkenning.utils import (
    get_digid_logo,
    get_eherkenning_logo,
)
from openforms.forms.models import Form

from ...base import BasePlugin, LoginLogo
from ...constants import CO_SIGN_PARAMETER, FORM_AUTH_SESSION_KEY, AuthAttribute
from ...exceptions import InvalidCoSignData
from ...registry import register
from .constants import (
    DIGID_MACHTIGEN_OIDC_AUTH_SESSION_KEY,
    DIGID_OIDC_AUTH_SESSION_KEY,
    EHERKENNING_BEWINDVOERING_OIDC_AUTH_SESSION_KEY,
    EHERKENNING_OIDC_AUTH_SESSION_KEY,
)


class OIDCAuthentication(BasePlugin):
    verbose_name = ""
    provides_auth = ""
    init_url = ""
    session_key = ""
    config_class = None

    def start_login(self, request: HttpRequest, form: Form, form_url: str):
        login_url = reverse(self.init_url, request=request)

        auth_return_url = reverse(
            "authentication:return",
            kwargs={"slug": form.slug, "plugin_id": self.identifier},
        )
        return_url = furl(auth_return_url).set(
            {
                "next": form_url,
            }
        )
        if co_sign_param := request.GET.get(CO_SIGN_PARAMETER):
            return_url.args[CO_SIGN_PARAMETER] = co_sign_param

        redirect_url = furl(login_url).set({"next": str(return_url)})
        return HttpResponseRedirect(str(redirect_url))

    def handle_co_sign(
        self, request: HttpRequest, form: Form
    ) -> Optional[Dict[str, Any]]:
        if not (claim := request.session.get(self.session_key)):
            raise InvalidCoSignData(f"Missing '{self.provides_auth}' parameter/value")
        return {
            "identifier": claim,
            "fields": {},
        }

    def add_claims_to_sessions_if_not_cosigning(self, claim, request):
        # set the session auth key only if we're not co-signing
        if claim and CO_SIGN_PARAMETER not in request.GET:
            request.session[FORM_AUTH_SESSION_KEY] = {
                "plugin": self.identifier,
                "attribute": self.provides_auth,
                "value": claim,
            }

    def handle_return(self, request, form):
        """
        Redirect to form URL.
        """
        form_url = request.GET.get("next")
        if not form_url:
            return HttpResponseBadRequest("missing 'next' parameter")

        claim = request.session.get(self.session_key)

        self.add_claims_to_sessions_if_not_cosigning(claim, request)

        return HttpResponseRedirect(form_url)

    def logout(self, request: HttpRequest):
        if "oidc_id_token" in request.session:
            logout_endpoint = self.config_class.get_solo().oidc_op_logout_endpoint
            if logout_endpoint:
                logout_url = furl(logout_endpoint).set(
                    {
                        "id_token_hint": request.session["oidc_id_token"],
                    }
                )
                requests.get(str(logout_url))

            del request.session["oidc_id_token"]

        if "oidc_login_next" in request.session:
            del request.session["oidc_login_next"]

        if self.session_key in request.session:
            del request.session[self.session_key]


@register("digid_oidc")
class DigiDOIDCAuthentication(OIDCAuthentication):
    verbose_name = _("DigiD via OpenID Connect")
    provides_auth = AuthAttribute.bsn
    init_url = "digid_oidc:init"
    session_key = DIGID_OIDC_AUTH_SESSION_KEY
    claim_name = ""
    config_class = OpenIDConnectPublicConfig

    def get_label(self) -> str:
        return "DigiD"

    def get_logo(self, request) -> Optional[LoginLogo]:
        return LoginLogo(title=self.get_label(), **get_digid_logo(request))


@register("eherkenning_oidc")
class eHerkenningOIDCAuthentication(OIDCAuthentication):
    verbose_name = _("eHerkenning via OpenID Connect")
    provides_auth = AuthAttribute.kvk
    init_url = "eherkenning_oidc:init"
    session_key = EHERKENNING_OIDC_AUTH_SESSION_KEY
    claim_name = "kvk"
    config_class = OpenIDConnectEHerkenningConfig

    def get_label(self) -> str:
        return "eHerkenning"

    def get_logo(self, request) -> Optional[LoginLogo]:
        return LoginLogo(title=self.get_label(), **get_eherkenning_logo(request))


@register("digid_machtigen_oidc")
class DigiDMachtigenOIDCAuthentication(OIDCAuthentication):
    verbose_name = _("DigiD Machtigen via OpenID Connect")
    provides_auth = AuthAttribute.bsn
    init_url = "digid_machtigen_oidc:init"
    session_key = DIGID_MACHTIGEN_OIDC_AUTH_SESSION_KEY
    config_class = OpenIDConnectDigiDMachtigenConfig

    def add_claims_to_sessions_if_not_cosigning(self, claim, request):
        # set the session auth key only if we're not co-signing
        if claim and CO_SIGN_PARAMETER not in request.GET:
            config = OpenIDConnectDigiDMachtigenConfig.get_solo()
            request.session[FORM_AUTH_SESSION_KEY] = {
                "plugin": self.identifier,
                "attribute": self.provides_auth,
                "value": claim[config.vertegenwoordigde_claim_name],
                "machtigen": request.session[DIGID_MACHTIGEN_OIDC_AUTH_SESSION_KEY],
            }

    def get_label(self) -> str:
        return "DigiD Machtigen"

    def get_logo(self, request) -> Optional[LoginLogo]:
        return LoginLogo(title=self.get_label(), **get_digid_logo(request))


@register("eherkenning_bewindvoering_oidc")
class EHerkenningBewindvoeringOIDCAuthentication(OIDCAuthentication):
    verbose_name = _("eHerkenning bewindvoering via OpenID Connect")
    provides_auth = AuthAttribute.kvk
    init_url = "eherkenning_bewindvoering_oidc:init"
    session_key = EHERKENNING_BEWINDVOERING_OIDC_AUTH_SESSION_KEY
    config_class = OpenIDConnectEHerkenningBewindvoeringConfig

    def add_claims_to_sessions_if_not_cosigning(self, claim, request):
        # set the session auth key only if we're not co-signing
        if claim and CO_SIGN_PARAMETER not in request.GET:
            config = self.config_class.get_solo()
            request.session[FORM_AUTH_SESSION_KEY] = {
                "plugin": self.identifier,
                "attribute": self.provides_auth,
                "value": claim[config.vertegenwoordigde_company_claim_name],
                "machtigen": request.session[
                    EHERKENNING_BEWINDVOERING_OIDC_AUTH_SESSION_KEY
                ],
            }

    def get_label(self) -> str:
        return "eHerkenning bewindvoering"

    def get_logo(self, request) -> Optional[LoginLogo]:
        return LoginLogo(title=self.get_label(), **get_eherkenning_logo(request))
