from os import getenv
from openai import OpenAI
from buggpt.prompts.PromptCommon import system_message
from buggpt.util.Logs import append_event, LLMEvent

with open(".openai_token", "r") as f:
    openai_key = f.read().strip()

openai = OpenAI(api_key=openai_key)

gpt4o_model = "gpt-4o-2024-05-13"
gpt4_model = "gpt-4-0125-preview"
gpt35_model = "gpt-3.5-turbo-0125"


class OpenAIGPT:
    def __init__(self, model):
        self.model = model

    def query(self, prompt, nb_samples=1):
        user_message = prompt.create_prompt()
        if len(user_message) > 10000:
            append_event(LLMEvent(pr_nb=-1,
                                  message=f"Query too long",
                                  content=f"System message:\n{system_message}\nUser message:\n{user_message}"))
            return ""

        append_event(LLMEvent(pr_nb=-1,
                              message=f"Querying {self.model}",
                              content=f"System message:\n{system_message}\nUser message:\n{user_message}"))

        if prompt.use_json_output:
            completion = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=4096,  # 4096 is the maximum token limit for gpt-4-0125-preview
                n=nb_samples,
                response_format={"type": "json_object"}
            )
        else:
            completion = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=4096,  # 4096 is the maximum token limit for gpt-4-0125-preview
                n=nb_samples
            )

        append_event(LLMEvent(pr_nb=-1,
                              message=f"Token usage",
                              content=f"prompt={completion.usage.prompt_tokens}, completion={completion.usage.completion_tokens}"))

        answers = []
        for choice in completion.choices:
            answers.append(choice.message.content)
        return answers
