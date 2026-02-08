"""Calculator plugin handlers. Safe evaluation via simpleeval."""
from typing import Union

try:
    from simpleeval import simple_eval, NameNotDefinedError
except ImportError:
    simple_eval = None
    NameNotDefinedError = Exception  # type: ignore


async def calculate(expression: str) -> str:
    """
    Evaluates a mathematical expression safely.
    Returns result string or error message.
    """
    if not simple_eval:
        return "Error: simpleeval is not installed."
    if not expression or not str(expression).strip():
        return "Error: expression is empty."
    expr = str(expression).strip()
    try:
        result = simple_eval(expr)
        if result is None:
            return "Error: expression did not produce a value."
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(result)
    except NameNotDefinedError as e:
        return f"Error: unknown symbol or function — {e!s}"
    except Exception as e:
        return f"Error: {e!s}"
