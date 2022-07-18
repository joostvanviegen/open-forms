from django.test import SimpleTestCase

from ..service import normalize_value_for_component


class NormalizationTests(SimpleTestCase):
    def test_postcode_normalization_with_space(self):
        component = {
            "type": "postcode",
            "inputMask": "9999 AA",
        }
        values = ["1015CJ", "1015 CJ", "1015 cj", "1015cj"]

        for value in values:
            with self.subTest(value=value):
                result = normalize_value_for_component(component, value)

                self.assertEqual(result.upper(), "1015 CJ")

    def test_postcode_normalization_without_space(self):
        component = {
            "type": "postcode",
            "inputMask": "9999AA",
        }
        values = ["1015CJ", "1015 CJ", "1015 cj", "1015cj"]

        for value in values:
            with self.subTest(value=value):
                result = normalize_value_for_component(component, value)

                self.assertEqual(result.upper(), "1015CJ")

    def test_empty_value(self):
        component = {
            "type": "postcode",
            "inputMask": "9999AA",
        }

        result = normalize_value_for_component(component, "")

        self.assertEqual(result, "")

    def test_value_invalid_for_mask(self):
        component = {
            "type": "postcode",
            "inputMask": "9999AA",
        }

        result = normalize_value_for_component(component, "AAAA 34")

        self.assertEqual(result, "AAAA 34")

    def test_no_input_mask_given(self):
        component = {"type": "postcode"}

        result = normalize_value_for_component(component, "AAAA 34")

        self.assertEqual(result, "AAAA 34")
