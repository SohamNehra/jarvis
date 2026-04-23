from langchain_core.tools import tool

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.
    Use this for any precise arithmetic or math calculation (e.g. '234 * 456 / 12').
    Supports standard operators: +, -, *, /, **, %."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"
