import json

class Prompt1:
    # NOTE: when changing the system message, must remove the old cache
    system_message = """
You are an experienced Java developer reviewing code for bugs.
"""

    instruction = """
Check the following code for correctness bugs.
If you find a bug, provide the buggy code line(s), a description of the bug, and its severity.
Most code you inspect is free of bugs.
If the code looks fine, provide an empty list of warnings.

Provide your answer as a JSON objects compatible with the following TypeScript interfaces:
```typescript
interface Answer {
    warnings: Warning[];
}

interface Warning {
    code: string[]; // copy the code line(s) that are buggy
    description: string; // give the reason why the code is buggy
    severity: int; // 1=lowest, 10=highest
}
```

Code to check:
```java
<CODE>
```

Answer:
```json
"""

    def __init__(self, code):
        self.code = code

    def create_prompt(self):
        prompt = self.instruction.replace("<CODE>", self.code)
        return prompt

    def parse_answer(self, raw_answer):
        try: 
            answer = json.loads(raw_answer)
        except json.JSONDecodeError:
            print("Invalid JSON")
            return None
    
        if "warnings" not in answer or not isinstance(answer["warnings"], list):
            print("Invalid JSON")
            return None
        
        for warning in answer["warnings"]:
            if "code" not in warning or "description" not in warning or "severity" not in warning:
                print("Invalid JSON")
                return None
            
            if not isinstance(warning["code"], list) or not all(isinstance(code, str) for code in warning["code"]):
                print("Invalid JSON")
                return None
        
            if not isinstance(warning["description"], str):
                print("Invalid JSON")
                return None
            
            if not isinstance(warning["severity"], int) or warning["severity"] < 1 or warning["severity"] > 10:
                print("Invalid JSON")
                return None

        return answer
        
