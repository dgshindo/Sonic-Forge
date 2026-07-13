from openai import OpenAI


class OpenAIService:

    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def ask(self, prompt, model="gpt-5.5"):
        response = self.client.responses.create(
            model=model,
            input=prompt
        )

        return response.output_text