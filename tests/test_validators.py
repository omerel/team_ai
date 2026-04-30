import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup import validate_nickname, NicknameError


class TestNicknameValidator(unittest.TestCase):
    def test_valid_simple(self):
        validate_nickname("rocky", existing=set())  # should not raise

    def test_valid_with_hyphen(self):
        validate_nickname("backend-bob", existing=set())

    def test_valid_with_digits(self):
        validate_nickname("agent42", existing=set())

    def test_rejects_uppercase(self):
        with self.assertRaises(NicknameError):
            validate_nickname("Rocky", existing=set())

    def test_rejects_starting_digit(self):
        with self.assertRaises(NicknameError):
            validate_nickname("1bot", existing=set())

    def test_rejects_starting_hyphen(self):
        with self.assertRaises(NicknameError):
            validate_nickname("-bot", existing=set())

    def test_rejects_underscore(self):
        with self.assertRaises(NicknameError):
            validate_nickname("rocky_bot", existing=set())

    def test_rejects_too_short(self):
        with self.assertRaises(NicknameError):
            validate_nickname("a", existing=set())

    def test_rejects_too_long(self):
        with self.assertRaises(NicknameError):
            validate_nickname("a" * 32, existing=set())

    def test_rejects_reserved(self):
        with self.assertRaises(NicknameError):
            validate_nickname("general-purpose", existing=set())

    def test_rejects_collision(self):
        with self.assertRaises(NicknameError):
            validate_nickname("rocky", existing={"rocky", "maya"})

    def test_empty_string(self):
        with self.assertRaises(NicknameError):
            validate_nickname("", existing=set())


if __name__ == "__main__":
    unittest.main()
