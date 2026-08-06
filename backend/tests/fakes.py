from app.services.llm.base import LLMMessage, LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    """Returns a pre-scripted sequence of responses, one per call to .chat().
    Lets us test agent/webhook logic without needing a real Ollama server
    running -- which this sandbox (and CI) can't provide anyway."""

    def __init__(self, responses: list[LLMResponse]):
        self.responses = list(responses)
        self.calls: list[list[LLMMessage]] = []
        self.tools_received: list = []

    def chat(self, messages, tools=None):
        self.calls.append(messages)
        self.tools_received.append(tools)
        return self.responses.pop(0)