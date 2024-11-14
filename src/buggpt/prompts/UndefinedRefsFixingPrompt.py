class UndefinedRefsFixingPrompt:
    def __init__(self, code, undefined_refs):
        self.code = code
        self.undefined_refs = undefined_refs

    def create_prompt(self):
        instruction_single = """
This Python code has an undefined reference to: <REF>. Fix it.

Respond only with Python code wrapped into ```python ... ```. Give no explanations.
"""

        instruction_multiple = """
This Python code has undefined references to: <REF>. Fix it.

Respond only with Python code wrapped into ```python ... ```. Give no explanations.
"""
        if len(self.undefined_refs) == 1:
            prompt = instruction_single.replace(
                "<REF>", self.undefined_refs[0])
        else:
            prompt = instruction_multiple.replace(
                "<REF>", ", ".join(self.undefined_refs))

        return prompt

    def parse_answer(self, raw_answer):
        code = ""
        in_code = False
        for line in raw_answer.split("\n"):
            if line.strip() == "```":
                break
            if in_code:
                code += line + "\n"
            if line == "```python" or line.startswith("import"):
                in_code = True
        return code
