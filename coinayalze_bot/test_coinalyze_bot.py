import os
from unittest.mock import patch

def test_load_api_key_from_env():
    # Import inside the test to allow patching before it evaluates global scope
    with patch('os.getenv', return_value='test_api_key') as mock_getenv, \
         patch('dotenv.load_dotenv') as mock_load_dotenv:
        from coinayalze_bot.coinalyze_bot import load_api_key

        api_key = load_api_key()

        mock_load_dotenv.assert_called_once()
        mock_getenv.assert_called_with('COINALYZE_API_KEY')
        assert api_key == 'test_api_key'
