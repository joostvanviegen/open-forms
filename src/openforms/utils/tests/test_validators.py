from django.core.exceptions import ValidationError
from django.test import TestCase

from ..validators import validate_bsn, validate_rsin


class BSNValidatorTestCase(TestCase):
    @staticmethod
    def test_valid_bsns():
        validate_bsn("063308836")
        validate_bsn("619183020")

    def test_invalid_bsns(self):
        with self.assertRaises(ValidationError):
            validate_bsn("06330883")

        with self.assertRaises(ValidationError):
            validate_bsn("063a08836")

        with self.assertRaises(ValidationError):
            validate_bsn("063-08836")


class RSINValidatorTestCase(TestCase):
    @staticmethod
    def test_valid_bsns():
        validate_rsin("063308836")
        validate_rsin("619183020")

    def test_invalid_bsns(self):
        with self.assertRaises(ValidationError):
            validate_rsin("06330883")

        with self.assertRaises(ValidationError):
            validate_rsin("063a08836")

        with self.assertRaises(ValidationError):
            validate_rsin("063-08836")
