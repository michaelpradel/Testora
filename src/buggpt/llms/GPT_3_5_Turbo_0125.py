from os import getenv
from openai import OpenAI

openai = OpenAI(api_key=getenv("OPENAI_KEY"))
model = "gpt-3.5-turbo-0125"


def query(prompt):
    print(
        f"System message:\n{prompt.system_message}\nUser message:\n{prompt.create_prompt()}")

    if prompt.use_json_output:
        completion = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt.system_message},
                {"role": "user", "content": prompt.create_prompt()}
            ],
            response_format={"type": "json_object"}
        )
    else:
        completion = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt.system_message},
                {"role": "user", "content": prompt.create_prompt()}
            ]
        )

    answer = completion.choices[0].message.content

    return answer
