import os
import unittest
from unittest.mock import MagicMock, patch

from ai_client import MistralClient, is_tier_restriction_error, FALLBACK_MODELS


class TestMistralClient(unittest.TestCase):
    def setUp(self):
        self.api_key = "test-api-key"

    def test_default_model_selection(self):
        with patch.dict(os.environ, {}, clear=True):
            client = MistralClient(api_key=self.api_key)
            self.assertEqual(client.model_id, "mistral-small-latest")

    def test_env_model_selection(self):
        with patch.dict(os.environ, {"MISTRAL_MODEL": "open-mistral-nemo"}, clear=True):
            client = MistralClient(api_key=self.api_key)
            self.assertEqual(client.model_id, "open-mistral-nemo")

    def test_explicit_model_selection(self):
        client = MistralClient(api_key=self.api_key, model_name="mistral-large-latest")
        self.assertEqual(client.model_id, "mistral-large-latest")

    def test_is_tier_restriction_error(self):
        err_msg = 'Status 403. Body: {"object":"error","message":"This model is not available in your subscription tier","type":"tier_not_allowed","code":"1910"}'
        self.assertTrue(is_tier_restriction_error(Exception(err_msg)))

        class CustomHttpError(Exception):
            status_code = 403

        self.assertTrue(is_tier_restriction_error(CustomHttpError("Forbidden")))

        self.assertFalse(is_tier_restriction_error(Exception("Connection timed out")))
        self.assertFalse(is_tier_restriction_error(Exception("500 Internal Server Error")))

    @patch("ai_client.Mistral")
    def test_successful_direct_generation(self, mock_mistral_class):
        mock_instance = MagicMock()
        mock_mistral_class.return_value = mock_instance

        mock_choice = MagicMock()
        mock_choice.message.content = '{"ideas": [{"project-title": "AI Tool", "tech-stack": "Python", "description": "Desc", "target-users": "Devs", "first-milestone": "MVP", "references": []}]}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_instance.chat.complete.return_value = mock_response

        client = MistralClient(api_key=self.api_key, model_name="mistral-small-latest")
        ideas = client.generate_project_ideas("Sample context with enough characters to pass validation test", idea_count=1)

        self.assertEqual(len(ideas), 1)
        self.assertEqual(ideas[0]["project-title"], "AI Tool")
        self.assertEqual(client.last_used_model, "mistral-small-latest")
        self.assertFalse(client.fallback_triggered)

    @patch("ai_client.Mistral")
    def test_auto_fallback_on_tier_not_allowed(self, mock_mistral_class):
        mock_instance = MagicMock()
        mock_mistral_class.return_value = mock_instance

        tier_error = Exception(
            'API error occurred: Status 403. Body: {"object":"error","message":"This model is not available in your subscription tier","type":"tier_not_allowed","param":null,"code":"1910","raw_status_code":403}'
        )

        mock_choice = MagicMock()
        mock_choice.message.content = '{"ideas": [{"title": "Fallback Idea", "stack": "Flask", "description": "Good idea", "users": "Everyone", "first_step": "Build prototype"}]}'
        mock_success_response = MagicMock()
        mock_success_response.choices = [mock_choice]

        # First call fails with tier error, second call (fallback model) succeeds
        mock_instance.chat.complete.side_effect = [tier_error, mock_success_response]

        client = MistralClient(api_key=self.api_key, model_name="mistral-large-latest")
        ideas = client.generate_project_ideas("Context about developer tools and machine learning", idea_count=1)

        self.assertEqual(len(ideas), 1)
        self.assertEqual(ideas[0]["project-title"], "Fallback Idea")
        self.assertTrue(client.fallback_triggered)
        self.assertEqual(client.last_used_model, "mistral-small-latest")
        # Ensure complete was called twice
        self.assertEqual(mock_instance.chat.complete.call_count, 2)

    @patch("ai_client.Mistral")
    def test_exhausted_fallbacks_raises_clear_error(self, mock_mistral_class):
        mock_instance = MagicMock()
        mock_mistral_class.return_value = mock_instance

        tier_error = Exception('Status 403: {"type":"tier_not_allowed","code":"1910"}')
        mock_instance.chat.complete.side_effect = tier_error

        client = MistralClient(api_key=self.api_key, model_name="mistral-large-latest")
        with self.assertRaises(ValueError) as ctx:
            client.generate_project_ideas("Sample context text", idea_count=1)

        self.assertIn("not available in your subscription tier", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
