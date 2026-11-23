from typing import Protocol

from pydantic import BaseModel

from ..core.config import Settings

# Newer Gemini models spend output tokens on reasoning; leave room for the JSON answer.
MAX_OUTPUT_TOKENS = 2048


class GeminiClient(Protocol):
    """Define the interface for structured Gemini responses."""

    def generate[T: BaseModel](self, system: str, prompt: str, schema: type[T]) -> T:
        """Generate a response conforming to the supplied schema."""
        ...


class VertexGeminiClient:
    """Use the SDK's HTTP timeout and Application Default Credentials."""

    def __init__(self, settings: Settings) -> None:
        from google import genai
        from google.genai import types

        options = types.HttpOptions(timeout=7500, retry_options=types.HttpRetryOptions(attempts=1))
        if settings.ai_provider == "apikey":
            self._client = genai.Client(vertexai=False, api_key=settings.google_api_key, http_options=options)
        else:
            self._client = genai.Client(
                vertexai=True,
                project=settings.gcp_project,
                location=settings.gemini_location,
                http_options=options,
            )
        self.model = settings.gemini_model

    def generate[T: BaseModel](self, system: str, prompt: str, schema: type[T]) -> T:
        """Request structured JSON from Gemini and validate the response."""
        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )
        return schema.model_validate_json(response.text or "")
