from os import getenv
from openai import OpenAI
from buggpt.prompts.PromptCommon import system_message
from buggpt.util.Logs import append_event, LLMEvent

openai = OpenAI(api_key=getenv("OPENAI_KEY"))
# model = "gpt-3.5-turbo-0125"
model = "gpt-4-0125-preview"


def query(prompt):
    append_event(LLMEvent(pr_nb=-1,
                          message=f"Querying {model}",
                          content=f"System message:\n{system_message}\nUser message:\n{prompt.create_prompt()}"))

    if prompt.use_json_output:
        completion = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt.create_prompt()}
            ],
            response_format={"type": "json_object"}
        )
    else:
        completion = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt.create_prompt()}
            ]
        )

    answer = completion.choices[0].message.content

    return answer
