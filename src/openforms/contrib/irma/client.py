import logging

from requests import RequestException
from zds_client import ClientError
from openfroms.contrib.irma.models import IrmaConfig

logger = logging.getLogger(__name__)

class IrmaClientError(Exception):
    pass

class IrmaClient:
    def startSession(self, **query_params):
        config = IrmaConfig.get_solo()
        if not config.service:
            logger.warning("no service defined for Irma client")
            raise IrmaClientError("no service defined")
    
        client = config.service.build_client()

        try:
            results = client.operation(
                "session",
                method="POST",
                data={
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
                }
            )
        except RequestException as e:
            logger.exception("exception while making Irma request", exc_info=e)
            return {}
        except ClientError as e:
            logger.exception("exception while making Irma request", exc_info=e)
            return {}

        values = dict()
        for attr in attributes:
            try:
                values[attr] = glom(data, attr)
            except GlomError:
                logger.warning(
                    f"missing expected attribute '{attr}' in backend response"
            )
        return values

    def endSession(self, **query_params):
        {
            
        }