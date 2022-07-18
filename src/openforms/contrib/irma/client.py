import logging

# from zds_client import ClientError
from requests import RequestException, Request, Session
import elasticapm
import json
from openforms.contrib.irma.models import IrmaConfig
from openforms.registrations.contrib.zgw_apis.tests.factories import ServiceFactory

logger = logging.getLogger(__name__)

class IrmaClientError(Exception):
    pass

class IrmaClient:
    @elasticapm.capture_span("app.irma")
    def startSession(self, **query_params):
        config = IrmaConfig.get_solo()
        config._service = ServiceFactory(
            api_root="http://10.1.0.134:8088",
            oas="http://localhost/irma_openapi.yaml"
        )
        print(config._service)
        if not config._service:
            logger.warning("no service defined for Irma client")
            raise IrmaClientError("no service defined")
        
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
            url = config._service.api_root + "session"
            request = Request('POST', url, data=data)
            prepped = request.prepare()

            prepped.headers['Content-Type'] = 'application/json'
            
            results = session.send(prepped)

        except RequestException as e:
            logger.exception("exception while making Irma request", exc_info=e)
            return {}

        #values = dict()
        #for attr in results:
        #    try:
        #        values[attr] = glom(data, attr)
        #    except GlomError:
        #        logger.warning(
        #            f"missing expected attribute '{attr}' in backend response"
        #    )
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