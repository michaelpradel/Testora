from json import JSONDecodeError
import time
from typing import List
from openai import OpenAI, RateLimitError
from buggpt.prompts.PromptCommon import system_message
from buggpt.util.Logs import append_event, LLMEvent
from buggpt.Config import model_version

if model_version.startswith("gpt"):
    with open(".openai_token_ExeCode", "r") as f:
        openai_key = f.read().strip()
        openai = OpenAI(api_key=openai_key)
elif model_version.startswith("deepseek"):
    with open(".openrouter_token", "r") as f:
        openrouter_key = f.read().strip()
        openai = OpenAI(api_key=openrouter_key,
                        base_url="https://openrouter.ai/api/v1")


class OpenAIGPT:
    def __init__(self):
        self.model = model_version

    def query(self, prompt, nb_samples=1, temperature=1) -> List:
        user_message = prompt.create_prompt()
        if len(user_message) > 30000:
            append_event(LLMEvent(pr_nb=-1,
                                  message=f"Query too long",
                                  content=f"System message:\n{system_message}\nUser message:\n{user_message}"))
            return [""]

        append_event(LLMEvent(pr_nb=-1,
                              message=f"Querying {self.model}",
                              content=f"System message:\n{system_message}\nUser message:\n{user_message}"))

        while True:
            try:
                if prompt.use_json_output:
                    completion = openai.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message}
                        ],
                        n=nb_samples,
                        response_format={"type": "json_object"},
                        temperature=temperature
                    )
                    break
                else:
                    completion = openai.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message}
                        ],
                        n=nb_samples,
                        temperature=temperature
                    )  # type: ignore[call-overload]

                    # handle errors that lead to no model being called
                    if completion.model is None:
                        append_event(LLMEvent(pr_nb=-1,
                                              message=f"Failed to get completion",
                                              content=f"Will try again in 1 second"))
                        time.sleep(1)
                        continue

                    append_event(LLMEvent(pr_nb=-1,
                                          message=f"Token usage",
                                          content=f"prompt={completion.usage.prompt_tokens}, completion={completion.usage.completion_tokens}"))

                    answers = []
                    for choice in completion.choices:
                        answers.append(choice.message.content)

                    # handle errors that lead to empty answers
                    if "" in answers:
                        append_event(LLMEvent(pr_nb=-1,
                                              message=f"Empty answer",
                                              content=f"Will try again in 1 second"))
                        time.sleep(1)
                        continue

                    return answers

            except RateLimitError as e:
                append_event(LLMEvent(pr_nb=-1,
                                      message=f"Rate limit exceeded",
                                      content=f"Will try again in 60 seconds"))
                time.sleep(60)
            except JSONDecodeError as e:
                append_event(LLMEvent(pr_nb=-1,
                                      message=f"JSON decode error",
                                      content=f"Will try again in 1 second"))
                time.sleep(1)

        raise Exception("Should not reach this point")
