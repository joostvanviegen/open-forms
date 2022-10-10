from django.test import TestCase

import requests_mock
from requests import RequestException
from zds_client import ClientError
from zgw_consumers.test import mock_service_oas_get

from openforms.contrib.irma.client import IrmaClient
from openforms.contrib.irma.tests.base import IrmaTestMixin

class IrmaClientTestCase(IrmaTestMixin, TestCase):
        #@request_mock.Mocker()
        def test_startSession(self):
            client = IrmaClient()
            res = client.start_session()

            self.assertIsNotNone(res)
            self.assertIsNotNone(res.json()["sessionPtr"])
            self.assertIsNotNone(res.json()["token"])

        def test_getSessionStatus(self):
            client = IrmaClient()
            client.start_session()
            res = client.check_session_status()
            print(res)

            self.assertIsNotNone(res)
            self.assertEqual(res.json(), "INITIALIZED")
