from os import getenv
from openai import OpenAI
from buggpt.prompts.PromptCommon import system_message
from buggpt.util.Logs import append_event, LLMEvent

openai = OpenAI(api_key=getenv("OPENAI_KEY"))
# model = "gpt-3.5-turbo-0125"
model = "gpt-4-0125-preview"


def query(prompt):
    user_message = prompt.create_prompt()
    if len(user_message) > 10000:
        append_event(LLMEvent(pr_nb=-1,
                              message=f"Query too long",
                              content=f"System message:\n{system_message}\nUser message:\n{user_message}"))
        return ""

    append_event(LLMEvent(pr_nb=-1,
                          message=f"Querying {model}",
                          content=f"System message:\n{system_message}\nUser message:\n{user_message}"))

    if prompt.use_json_output:
        completion = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=10000,
            response_format={"type": "json_object"}
        )
    else:
        completion = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=4096 # 4096 is the maximum token limit for gpt-4-0125-preview
        )

    answer = completion.choices[0].message.content

    return answer
