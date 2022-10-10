import logging

# from zds_client import ClientError
from requests import RequestException, Request, Session
import elasticapm
import json
import factory
from zgw_consumers.models import Service
from openforms.contrib.irma.models import IrmaConfig
#from openforms.registrations.contrib.zgw_apis.tests.factories import ServiceFactory

logger = logging.getLogger(__name__)

class IrmaClientError(Exception):
    pass

class IrmaClient:
    session_ptr = {"url": '', "qr": ''}
    token = None
    root_url = "http://10.1.0.134:8088"
    config = None

    def config_session(self):
        self.config = IrmaConfig.get_solo()
        self.config._service = ServiceFactory(
            api_root=self.root_url,
            oas="http://localhost/irma_openapi.yaml"
        )
        print(self.config._service)
        if not self.config._service:
            logger.warning("no service defined for Irma client")
            raise IrmaClientError("no service defined")

    @elasticapm.capture_span("app.irma")
    def start_session(self, **query_params): 
        if(self.config is None):
            self.config_session()
        results = None
        try:
            session = Session()

            data=json.dumps({
                    "@context": "https://irma.app/ld/request/disclosure/v2",
                    "disclose": [
                      [
                        [ "irma-demo.MijnOverheid.root.BSN" ]
                      ],
                      [
                        [
                          "irma-demo.nijmegen.address.street",
                          "irma-demo.nijmegen.address.houseNumber",
                          "irma-demo.nijmegen.address.city"
                        ],
                        [
                          "irma-demo.idin.idin.address",
                          "irma-demo.idin.idin.city"
                        ]
                      ]
                    ]
                })
            url = self.config._service.api_root + "session"
            request = Request('POST', url, data=data)
            prepped = request.prepare()

            prepped.headers['Content-Type'] = 'application/json'
            
            results = session.send(prepped)

        except RequestException as e:
            logger.exception("exception while making Irma request", exc_info=e)
            return {}
        self.session_ptr["url"] = results.json()["sessionPtr"]["u"]
        self.session_ptr["qr"] = results.json()["sessionPtr"]["irmaqr"]
        self.token = results.json()["token"]

        return results
  
    @elasticapm.capture_span("app.irma")
    def check_session_status(self, **query_params):
        print(self.session_ptr["url"])
        if(self.config is None):
            self.config_session()
        results = None
        try:
            session = Session()

            url = self.config._service.api_root + "session/" + self.token + "/status"
            request = Request('get', url)
            prepped = request.prepare()

            prepped.headers['Content-Type'] = 'application/json'
            
            results = session.send(prepped)

        except RequestException as e:
            logger.exception("exception while making Irma request", exc_info=e)
            return {}

        return results

    #def endSession(self, **query_params):
    #    {
    #        config = IrmaConfig.get_solo()
    #        if not config.service:
    #            logger.warning("no service defined for Irma client")
    #            raise IrmaClientError("no service defined")
#
    #        client = config.service.build_client()
#
    #        try:
    #            results = client.operation(
    #                "session",
    #                method="DELETE",
    #                data=**query_params.data
    #            )
    #    }

class ServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model=Service
