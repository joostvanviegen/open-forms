import factory

from openforms.products.tests.factories import ProductFactory

from ..constants import FormVariableDataTypes, FormVariableSources
from ..models import FormStep, FormVariable
from ..utils import form_to_json


class FormFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Form %03d" % n)
    slug = factory.Faker("word")
    active = True
    product = factory.SubFactory(ProductFactory)
    category = factory.SubFactory("openforms.forms.tests.factories.CategoryFactory")
    payment_backend = ""
    # factory-boy ignores attributes starting with an underscore so we'll use Meta.rename
    deleted_ = False

    class Meta:
        model = "forms.Form"
        rename = {"deleted_": "_is_deleted"}

    class Params:
        generate_minimal_setup = factory.Trait(
            formstep=factory.RelatedFactory(
                "openforms.forms.tests.factories.FormStepFactory",
                factory_related_name="form",
            ),
        )


class FormDefinitionFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "FormDefinition %03d" % n)

    slug = factory.Sequence(lambda n: f"fd-{n}")
    login_required = False
    configuration = factory.Sequence(
        lambda n: {"components": [{"type": "textfield", "key": f"test-key-{n}"}]}
    )

    class Meta:
        model = "forms.FormDefinition"

    class Params:
        is_appointment = factory.Trait(
            configuration={
                "display": "form",
                "components": [
                    {
                        "key": "product",
                        "type": "textfield",
                        "appointments": {"showProducts": True},
                        "label": "Product",
                    },
                    {
                        "key": "location",
                        "type": "textfield",
                        "appointments": {"showLocations": True},
                        "label": "Location",
                    },
                    {
                        "key": "time",
                        "type": "textfield",
                        "appointments": {"showTimes": True},
                        "label": "Time",
                    },
                    {
                        "key": "lastName",
                        "type": "textfield",
                        "appointments": {"lastName": True},
                        "label": "Last Name",
                    },
                    {
                        "key": "birthDate",
                        "type": "date",
                        "appointments": {"birthDate": True},
                        "label": "Date of Birth",
                    },
                ],
            }
        )


class FormStepFactory(factory.django.DjangoModelFactory):
    form_definition = factory.SubFactory(FormDefinitionFactory)
    form = factory.SubFactory(FormFactory)

    class Meta:
        model = "forms.FormStep"

    @classmethod
    def create(
        cls,
        **kwargs,
    ) -> FormStep:
        form_step = super().create(**kwargs)
        FormVariable.objects.create_for_formstep(form_step)
        return form_step


class FormVersionFactory(factory.django.DjangoModelFactory):
    form = factory.SubFactory(FormFactory)
    export_blob = {}

    class Meta:
        model = "forms.FormVersion"

    @factory.post_generation
    def post(obj, create, extracted, **kwargs):
        json_form = form_to_json(obj.form.id)
        obj.export_blob = json_form
        obj.save()


class FormLogicFactory(factory.django.DjangoModelFactory):
    json_logic_trigger = {"==": [{"var": "test-key"}, 1]}
    actions = [{"action": {"type": "disable-next"}}]

    class Meta:
        model = "forms.FormLogic"


class FormPriceLogicFactory(factory.django.DjangoModelFactory):
    form = factory.SubFactory(FormFactory)
    json_logic_trigger = {"==": [{"var": "test-key"}, 1]}
    price = factory.Faker(
        "pydecimal",
        left_digits=2,
        right_digits=2,
        positive=True,
        min_value=5.00,
        max_value=100.00,
    )

    class Meta:
        model = "forms.FormPriceLogic"


class FormVariableFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Variable %03d" % n)
    form = factory.SubFactory(FormFactory)
    key = factory.Faker("word")
    form_definition = factory.SubFactory(FormDefinitionFactory)
    source = FormVariableSources.user_defined
    data_type = FormVariableDataTypes.string
    initial_value = None

    class Meta:
        model = "forms.FormVariable"


class CategoryFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Category %03d" % n)

    class Meta:
        model = "forms.Category"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # defer creation to treebeard instead of fuzzing the underlying DB fields
        parent = kwargs.pop("parent", None)
        if parent is not None:
            return parent.add_child(**kwargs)
        return model_class.add_root(**kwargs)
