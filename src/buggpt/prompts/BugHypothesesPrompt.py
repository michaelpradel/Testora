import json


class BugHypothesesPrompt:
    # NOTE: when changing the system message, must remove the old cache
    system_message = """
You are an experienced Python developer.
"""

    instruction = """
Do you see any bugs in this code?
```python
<CODE>
```
The code is extracted from a larger context, and you can assume that all necessary imports, other functions, and global variables are available.
Focus on logic errors, incorrect assumptions, and missing corner cases.
"""

    json_instruction = """
Provide your answer as a JSON object compatible with the "Answer" TypeScript interface:
```typescript
interface Bug {
    explanation: string;
}

interface Answer {
    bugs: Bug[];
}
```

Answer:
```json
"""

    output_instruction = """
Provide your answer as an enumerated list, with one bug on each line.
"""

    def __init__(self, code):
        self.code = code
        self.json = False

    def create_prompt(self):
        if self.json:
            prompt = self.instruction.replace("<CODE>", self.code) + self.json_instruction
        else:
            prompt = self.instruction.replace("<CODE>", self.code) + self.output_instruction
        return prompt

    def parse_answer(self, raw_answer):
        if self.json:
            try:
                answer = json.loads(raw_answer)
            except json.JSONDecodeError:
                print("Invalid JSON")
                return None

            if "bugs" not in answer or not isinstance(answer["bugs"], list):
                print("Invalid JSON")
                return None

            for bug in answer["bugs"]:
                if "explanation" not in bug:
                    print("Invalid JSON")
                    return None

                if not isinstance(bug["explanation"], str):
                    print("Invalid JSON")
                    return None

            return answer
        else:
            lines = raw_answer.split("\n")
            answer = {"bugs": []}
            for line in lines:
                if any([line.startswith(f"{nb}.") for nb in range(1, 10)]):
                    _, _, cleaned_line = line.partition(".")
                    cleaned_line = cleaned_line.strip()
                    answer["bugs"].append({"explanation": cleaned_line})
            return answer
