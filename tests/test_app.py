import unittest
from unittest.mock import MagicMock, patch

from app import app, MODEL_OPTIONS


class TestAppRoutes(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_index_get_renders_form_and_models(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Mistral model", html)
        self.assertIn("mistral-small-latest", html)
        self.assertIn("open-mistral-nemo", html)

    def test_index_post_missing_api_key_flashes_error(self):
        response = self.client.post("/", data={"api_key": ""}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Add your Mistral API key before generating ideas.", html)

    @patch("app.SourceParser")
    @patch("app.MistralClient")
    def test_index_post_success_with_fallback_warning(self, mock_mistral_client_class, mock_parser_class):
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.return_value = (
            "This is a detailed technical architecture document with plenty of content to pass "
            "minimum length checks and ensure complete validation succeeds across all pipeline components."
        )
        mock_parser_class.return_value = mock_parser_instance

        mock_client_instance = MagicMock()
        mock_client_instance.generate_project_ideas.return_value = [
            {
                "project-title": "Smart DevOps Agent",
                "tech-stack": "Python, Docker",
                "description": "An agent that auto-monitors deployment health.",
                "target-users": "Site Reliability Engineers",
                "first-milestone": "Build monitoring probe",
                "references": [],
            }
        ]
        mock_client_instance.fallback_triggered = True
        mock_client_instance.last_used_model = "mistral-small-latest"
        mock_mistral_client_class.return_value = mock_client_instance

        response = self.client.post(
            "/",
            data={
                "api_key": "valid-fake-key",
                "model_name": "mistral-large-latest",
                "idea_count": 3,
                "focus_area": "Developer tools",
                "source_mode": "url",
                "url_input": "https://example.com/docs",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Smart DevOps Agent", html)
        self.assertIn("using fallback model &#39;mistral-small-latest&#39;", html)


if __name__ == "__main__":
    unittest.main()
