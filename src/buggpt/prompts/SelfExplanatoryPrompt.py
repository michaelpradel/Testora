import json


class SelfExplanatoryPrompt:
    def __init__(self, fut_code):
        self.fut_code = fut_code
        self.use_json_output = True

    def create_prompt(self):
        prompt_template_code_part = """
Consider this Python function:
```python
<CODE>
```
"""
        prompt_questions_part = """
Answer these questions about the function:
1) Is the purpose of the function clear?
2) Based on your understanding of the function's purpose, could you predict what output the function should have for any given input?
"""
        prompt_instruction_part = """
Respond with a JSON object that follows this format:
```json
{
  "1": "no",
  "2": "yes"
}
```

Answer:
```json
"""

        prompt = prompt_template_code_part.replace("<CODE>", self.fut_code)
        prompt += prompt_questions_part
        prompt += prompt_instruction_part

        return prompt

    def parse_answer(self, raw_answer):
        try:
            answer = json.loads(raw_answer)
        except json.JSONDecodeError:
            print("Invalid JSON")
            return None

        try:
            purpose_clear = answer["1"] == "yes"
            clear_io = answer["2"] == "yes"

            keep = purpose_clear and clear_io

            if not keep:
                print(f"LLM removes this function:\n{self.fut_code}")
                print("Reasons:")
                if not purpose_clear:
                    print(" * purpose is not clear")
                if not clear_io:
                    print(" * unclear inputs/outputs")

            return keep
        except KeyError as e:
            print(f"Missing key in JSON: {e}")
            return None
