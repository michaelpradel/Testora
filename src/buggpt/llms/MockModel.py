def query(prompt):
    print(f"System message:\n{prompt.system_message}\nUser message:\n{prompt.create_prompt()}")
    return '{"warnings": [{"code": ["some_code"], "description": "bug", "severity": 5}]}'