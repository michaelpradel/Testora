from openai import OpenAI
from testora.prompts.RegressionClassificationPromptV2 import RegressionClassificationPromptV2
from testora.prompts.PromptCommon import system_message

with open(".openai_token", "r") as f:
    openai_key = f.read().strip()

openai = OpenAI(api_key=openai_key)
gpt4o_model = "gpt-4o-2024-05-13"

with open("data/example_prompts/intended1.txt", "r") as f:
    intended_prompt1 = f.read()

with open("data/example_prompts/intended2.txt", "r") as f:
    intended_prompt2 = f.read()

with open("data/example_prompts/intended3.txt", "r") as f:
    intended_prompt3 = f.read()

with open("data/example_prompts/surprising1.txt", "r") as f:
    surprising_prompt1 = f.read()

with open("data/example_prompts/surprising2.txt", "r") as f:
    surprising_prompt2 = f.read()


def call_model(prompt, temperature):
    completion = openai.chat.completions.create(
        model=gpt4o_model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        max_tokens=4096,  # 4096 is the maximum token limit for gpt-4-0125-preview
        n=1,
        temperature=temperature
    )
    return completion.choices[0].message.content


if __name__ == "__main__":
    intended = [intended_prompt1, intended_prompt2, intended_prompt3]
    surprising = [surprising_prompt1, surprising_prompt2]
    r = RegressionClassificationPromptV2("", "", "", "", "", "")

    for idx, prompt in enumerate(intended):
        print(f"Intended prompt {idx + 1}:")
        for temperature in [0, 0.2, 0.7, 1.0]:
            answer = call_model(prompt, temperature)
            is_relevant_change, is_deterministic, is_public, is_legal, is_surprising = r.parse_answer(
                [answer])
            print(f"  temp={temperature} gives surprising={is_surprising}")

    print()
    for idx, prompt in enumerate(surprising):
        print(f"Surprising prompt {idx + 1}:")
        for temperature in [0, 0.2, 0.7, 1.0]:
            answer = call_model(prompt, temperature)
            is_relevant_change, is_deterministic, is_public, is_legal, is_surprising = r.parse_answer(
                [answer])
            print(f"  temp={temperature} gives surprising={is_surprising}")
