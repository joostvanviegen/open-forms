import logging
from multiprocessing.connection import Client
import random
from typing import Any, Dict, List

from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from requests import RequestException

from openforms.submissions.models import Submission

from openforms.contrib.irma.models import IrmaConfig
from openforms.contrib.irma.client import IrmaClient, IrmaClientError

from ...base import BasePlugin
from ...registry import register
from .constants import Attributes

logger = logging.getLogger(__name__)

CALLBACKS = {
    Attributes.random_number: lambda: random.randint(1000, 10_000),
    Attributes.random_string: get_random_string,
}


@register("irma")
class IrmaPrefill(BasePlugin):
    verbose_name = _("Irma")

    def get_available_attributes(self):
        return Attributes.choices

    def get_prefill_values(
        self, submission: Submission, attributes: List[str]
    ) -> Dict[str, Any]:

      if not submission.irma:
        return {}

      config = IrmaConfig.get_solo()
      if not config.service:
          logger.warning("no service defined for Irma prefill")
          return {}

      client = config.service.build_client()

      try:
        data = client.submit(
          {
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
        return {attr: CALLBACKS[attr]() for attr in attributes}
      except RequestException as e:
        logger.exception("exception while making request", exc_info=e)
        return {}
