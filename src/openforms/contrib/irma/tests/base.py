import json
import os

from openforms.contrib.irma.models import IrmaConfig
from openforms.registrations.contrib.zgw_apis.tests.factories import ServiceFactory

class IrmaTestMixin:
    # def load_json_mock(self, name):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        #config = IrmaConfig.get_solo()
        #config._service = ServiceFactory(
        #    api_root="http://localhost:8088",
        #    oas="http://localhost/irma_openapi.yaml"
        #)
        #config = IrmaConfig.get_solo()
        # Do things to change the config as needed
        #config.save()