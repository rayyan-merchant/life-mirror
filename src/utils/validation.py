from guardrails import Guard
from functools import wraps

def guardrails_validate(input_schema, output_schema):
    guard = Guard.from_pydantic(output_schema)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # Validate output
            validated_output = guard.parse(result.dict())
            return validated_output
        return wrapper
    return decorator
