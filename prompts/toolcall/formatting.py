TOOLCALL_FORMAT_INSTRUCTION = """
The output MUST strictly adhere to the following JSON format, and NO other text MUST be included.
The example formats are as follows. If no function call is needed, please directly output an empty list '[]'

For single screenshot:
```
[
    {"name": "take_screenshot", "arguments": {}}
]
```

When NO tool call is needed, output EXACTLY:
```
[]
```
"""