from typing import Type

from openforms.plugins.registry import BaseRegistry

from .nodes import ComponentNode


class Registry(BaseRegistry):
    module = "formio"

    def __call__(self, unique_identifier: str, *args, **kwargs) -> callable:
        """
        Overridden from base class because we register classes instead of instances.
        """

        def decorator(klass: Type[ComponentNode]) -> Type[ComponentNode]:
            if unique_identifier in self._registry:
                raise ValueError(
                    f"The unique identifier '{unique_identifier}' is already present "
                    "in the registry."
                )
            if not issubclass(klass, ComponentNode):
                raise TypeError("Node class must subclass 'ComponentNode'")
            self._registry[unique_identifier] = klass
            return klass

        return decorator

    def __getitem__(self, key: str) -> Type[ComponentNode]:
        try:
            return self._registry[key]
        except KeyError:
            return ComponentNode


register = Registry()
