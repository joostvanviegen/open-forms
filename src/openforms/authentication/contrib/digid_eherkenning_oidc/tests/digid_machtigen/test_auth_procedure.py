from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

import requests_mock
from furl import furl
from rest_framework import status

from digid_eherkenning_oidc_generics.models import (
    OpenIDConnectDigiDMachtigenConfig,
    OpenIDConnectPublicConfig,
)
from openforms.authentication.views import BACKEND_OUTAGE_RESPONSE_PARAMETER
from openforms.forms.tests.factories import FormFactory

default_config = dict(
    enabled=True,
    oidc_rp_client_id="testclient",
    oidc_rp_client_secret="secret",
    oidc_rp_sign_algo="RS256",
    oidc_rp_scopes_list=["openid", "bsn"],
    oidc_op_jwks_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/certs",
    oidc_op_authorization_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/auth",
    oidc_op_token_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/token",
    oidc_op_user_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/userinfo",
)


@override_settings(CORS_ALLOW_ALL_ORIGINS=True, IS_HTTPS=True)
@patch(
    "digid_eherkenning_oidc_generics.models.OpenIDConnectDigiDMachtigenConfig.get_solo",
    return_value=OpenIDConnectDigiDMachtigenConfig(**default_config),
)
class DigiDMachtigenOIDCTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.form = FormFactory.create(
            generate_minimal_setup=True,
            authentication_backends=["digid_machtigen_oidc"],
        )

    def test_redirect_to_digid_machtigen_oidc(self, m_get_solo):
        login_url = reverse(
            "authentication:start",
            kwargs={"slug": self.form.slug, "plugin_id": "digid_machtigen_oidc"},
        )

        form_path = reverse("core:form-detail", kwargs={"slug": self.form.slug})
        form_url = furl(f"http://testserver{form_path}").set({"_start": "1"}).url
        start_url = furl(login_url).set({"next": form_url})
        response = self.client.get(start_url)

        self.assertEqual(status.HTTP_302_FOUND, response.status_code)

        parsed = furl(response.url)
        query_params = parsed.query.params

        self.assertEqual(parsed.host, "testserver")
        self.assertEqual(
            parsed.path, reverse("digid_machtigen_oidc:oidc_authentication_init")
        )

        parsed = furl(query_params["next"])
        query_params = parsed.query.params

        self.assertEqual(
            parsed.path,
            reverse(
                "authentication:return",
                kwargs={"slug": self.form.slug, "plugin_id": "digid_machtigen_oidc"},
            ),
        )
        self.assertEqual(query_params["next"], form_url)

        with requests_mock.Mocker() as m:
            m.head(
                "http://provider.com/auth/realms/master/protocol/openid-connect/auth",
                status_code=200,
            )
            response = self.client.get(response.url)

        self.assertEqual(status.HTTP_302_FOUND, response.status_code)

        parsed = furl(response.url)
        query_params = parsed.query.params

        self.assertEqual(parsed.host, "provider.com")
        self.assertEqual(
            parsed.path, "/auth/realms/master/protocol/openid-connect/auth"
        )
        self.assertEqual(query_params["scope"], "openid bsn")
        self.assertEqual(query_params["client_id"], "testclient")
        self.assertEqual(
            query_params["redirect_uri"],
            f"http://testserver{reverse('digid_machtigen_oidc:oidc_authentication_callback')}",
        )

        parsed = furl(self.client.session["oidc_login_next"])
        query_params = parsed.query.params

        self.assertEqual(
            parsed.path,
            reverse(
                "authentication:return",
                kwargs={"slug": self.form.slug, "plugin_id": "digid_machtigen_oidc"},
            ),
        )
        self.assertEqual(query_params["next"], form_url)

    def test_redirect_to_digid_machtigen_oidc_internal_server_error(self, m_get_solo):
        login_url = reverse(
            "authentication:start",
            kwargs={"slug": self.form.slug, "plugin_id": "digid_machtigen_oidc"},
        )

        form_path = reverse("core:form-detail", kwargs={"slug": self.form.slug})
        form_url = str(furl(f"http://testserver{form_path}").set({"_start": "1"}))
        start_url = furl(login_url).set({"next": form_url})
        response = self.client.get(start_url)

        self.assertEqual(status.HTTP_302_FOUND, response.status_code)

        with requests_mock.Mocker() as m:
            m.head(
                "http://provider.com/auth/realms/master/protocol/openid-connect/auth",
                status_code=500,
            )
            response = self.client.get(response.url)

        parsed = furl(response.url)
        query_params = parsed.query.params

        self.assertEqual(parsed.host, "testserver")
        self.assertEqual(parsed.path, form_path)
        self.assertEqual(query_params["of-auth-problem"], "digid_machtigen_oidc")

    def test_redirect_to_digid_machtigen_oidc_callback_error(self, m_get_solo):
        form_path = reverse("core:form-detail", kwargs={"slug": self.form.slug})
        form_url = f"http://testserver{form_path}"
        redirect_form_url = furl(form_url).set({"_start": "1"})
        redirect_url = furl(
            reverse(
                "authentication:return",
                kwargs={"slug": self.form.slug, "plugin_id": "digid_machtigen_oidc"},
            )
        ).set({"next": redirect_form_url})

        session = self.client.session
        session["oidc_login_next"] = redirect_url.url
        session.save()

        with patch(
            "openforms.authentication.contrib.digid_eherkenning_oidc.backends.OIDCAuthenticationDigiDMachtigenBackend.verify_claims",
            return_value=False,
        ):
            response = self.client.get(reverse("digid_machtigen_oidc:callback"))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

        parsed = furl(response.url)
        query_params = parsed.query.params

        self.assertEqual(parsed.path, form_path)
        self.assertEqual(query_params["_start"], "1")
        self.assertEqual(
            query_params[BACKEND_OUTAGE_RESPONSE_PARAMETER], "digid_machtigen_oidc"
        )

    @override_settings(CORS_ALLOW_ALL_ORIGINS=False, CORS_ALLOWED_ORIGINS=[])
    def test_redirect_to_disallowed_domain(self, m_get_solo):
        login_url = reverse(
            "digid_machtigen_oidc:oidc_authentication_init",
        )

        form_url = "http://example.com"
        start_url = furl(login_url).set({"next": form_url})
        response = self.client.get(start_url)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    @override_settings(
        CORS_ALLOW_ALL_ORIGINS=False, CORS_ALLOWED_ORIGINS=["http://example.com"]
    )
    def test_redirect_to_allowed_domain(self, m_get_solo):
        m_get_solo.return_value = OpenIDConnectDigiDMachtigenConfig(
            enabled=True,
            oidc_rp_client_id="testclient",
            oidc_rp_client_secret="secret",
            oidc_rp_sign_algo="RS256",
            oidc_rp_scopes_list=["openid", "bsn"],
            oidc_op_jwks_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/certs",
            oidc_op_authorization_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/auth",
            oidc_op_token_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/token",
            oidc_op_user_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/userinfo",
        )

        login_url = reverse(
            "authentication:start",
            kwargs={"slug": self.form.slug, "plugin_id": "digid_machtigen_oidc"},
        )

        form_url = "http://example.com"
        start_url = furl(login_url).set({"next": form_url})
        response = self.client.get(start_url)

        self.assertEqual(status.HTTP_302_FOUND, response.status_code)

        parsed = furl(response.url)
        query_params = parsed.query.params

        self.assertEqual(parsed.host, "testserver")
        self.assertEqual(
            parsed.path, reverse("digid_machtigen_oidc:oidc_authentication_init")
        )

        parsed = furl(query_params["next"])
        query_params = parsed.query.params

        self.assertEqual(
            parsed.path,
            reverse(
                "authentication:return",
                kwargs={"slug": self.form.slug, "plugin_id": "digid_machtigen_oidc"},
            ),
        )
        self.assertEqual(query_params["next"], form_url)

        with requests_mock.Mocker() as m:
            m.head(
                "http://provider.com/auth/realms/master/protocol/openid-connect/auth",
                status_code=200,
            )
            response = self.client.get(response.url)

        self.assertEqual(status.HTTP_302_FOUND, response.status_code)

        parsed = furl(response.url)
        query_params = parsed.query.params

        self.assertEqual(parsed.host, "provider.com")
        self.assertEqual(
            parsed.path, "/auth/realms/master/protocol/openid-connect/auth"
        )
        self.assertEqual(query_params["scope"], "openid bsn")
        self.assertEqual(query_params["client_id"], "testclient")
        self.assertEqual(
            query_params["redirect_uri"],
            f"http://testserver{reverse('digid_machtigen_oidc:oidc_authentication_callback')}",
        )

    def test_redirect_with_keycloak_identity_provider_hint(self, m_get_solo):
        m_get_solo.return_value = OpenIDConnectPublicConfig(
            enabled=True,
            oidc_rp_client_id="testclient",
            oidc_rp_client_secret="secret",
            oidc_rp_sign_algo="RS256",
            oidc_rp_scopes_list=["openid", "bsn"],
            oidc_op_jwks_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/certs",
            oidc_op_authorization_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/auth",
            oidc_op_token_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/token",
            oidc_op_user_endpoint="http://provider.com/auth/realms/master/protocol/openid-connect/userinfo",
            oidc_keycloak_idp_hint="oidc-digid-machtigen",
        )

        login_url = reverse(
            "authentication:start",
            kwargs={"slug": self.form.slug, "plugin_id": "digid_machtigen_oidc"},
        )

        form_path = reverse("core:form-detail", kwargs={"slug": self.form.slug})
        form_url = str(furl(f"http://testserver{form_path}").set({"_start": "1"}))
        start_url = furl(login_url).set({"next": form_url})
        response = self.client.get(start_url)

        self.assertEqual(status.HTTP_302_FOUND, response.status_code)

        parsed = furl(response.url)
        query_params = parsed.query.params

        self.assertEqual(parsed.host, "testserver")
        self.assertEqual(
            parsed.path, reverse("digid_machtigen_oidc:oidc_authentication_init")
        )

        parsed = furl(query_params["next"])
        query_params = parsed.query.params

        self.assertEqual(
            parsed.path,
            reverse(
                "authentication:return",
                kwargs={"slug": self.form.slug, "plugin_id": "digid_machtigen_oidc"},
            ),
        )
        self.assertEqual(query_params["next"], form_url)

        with requests_mock.Mocker() as m:
            m.head(
                "http://provider.com/auth/realms/master/protocol/openid-connect/auth",
                status_code=200,
            )
            response = self.client.get(response.url)

        self.assertEqual(status.HTTP_302_FOUND, response.status_code)

        parsed = furl(response.url)
        query_params = parsed.query.params

        self.assertEqual(parsed.host, "provider.com")
        self.assertEqual(
            parsed.path, "/auth/realms/master/protocol/openid-connect/auth"
        )
        self.assertEqual(query_params["scope"], "openid bsn")
        self.assertEqual(query_params["client_id"], "testclient")
        self.assertEqual(
            query_params["redirect_uri"],
            f"http://testserver{reverse('digid_machtigen_oidc:oidc_authentication_callback')}",
        )
        self.assertEqual(query_params["kc_idp_hint"], "oidc-digid-machtigen")
