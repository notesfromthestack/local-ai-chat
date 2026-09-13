import httpx
from typing import List

import logging

from api.app.config import settings
from api.app.models import (
    OllamaChatRequest,
    OllamaChatResponse,
    OllamaMessage,
)

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def chat(
        self,
        messages: List[OllamaMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
    ) -> OllamaChatResponse:
        """
        Send chat completion request to Ollama.
        """
        model_name = model or self.model

        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        request = OllamaChatRequest(
            model=model_name,
            messages=messages,
            stream=False,
            options=options,
        )

        logger.info(f"Sending request to Ollama: {self.base_url}/api/chat")
        logger.debug(f"Request: {request.model_dump()}")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=request.model_dump(),
                )
                response.raise_for_status()

                data = response.json()
                logger.debug(f"Ollama response: {data}")

                return OllamaChatResponse(**data)

        except httpx.HTTPError as e:
            logger.error(f"Ollama request failed: {e}")
            raise
