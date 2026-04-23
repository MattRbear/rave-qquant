import unittest
from unittest.mock import patch
from config.validation import validate_environment

class TestValidation(unittest.TestCase):

    @patch.dict('os.environ', {'COINALYZE_API_KEY': 'dummy_key'}, clear=True)
    def test_validate_environment_success(self):
        is_valid, messages = validate_environment()
        self.assertTrue(is_valid)
        self.assertEqual(messages, [])

    @patch.dict('os.environ', {}, clear=True)
    def test_validate_environment_missing_key(self):
        is_valid, messages = validate_environment()
        self.assertFalse(is_valid)
        self.assertGreaterEqual(len(messages), 1)
        # Check for presence of the required key in the error messages.
        found_message = any("COINALYZE_API_KEY" in msg for msg in messages)
        self.assertTrue(found_message)

if __name__ == '__main__':
    unittest.main()
