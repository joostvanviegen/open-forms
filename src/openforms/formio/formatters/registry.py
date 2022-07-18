from typing import Any

from openforms.plugins.registry import BaseRegistry

from ..typing import Component


class Registry(BaseRegistry):
    """
    A registry for the FormIO formatters.
    """

    def format(self, info: Component, value: Any, as_html=False):
        formatter = (
            register[info["type"]] if info["type"] in register else register["default"]
        )
        return formatter(info, value, as_html=as_html)


# Sentinel to provide the default registry. You can easily instantiate another
# :class:`Registry` object to use as dependency injection in tests.
register = Registry()
