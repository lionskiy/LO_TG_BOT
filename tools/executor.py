"""
Tool executor: executes tool calls via registry handlers.
"""
import asyncio
import logging
from typing import List, Optional

from tools.models import ToolCall, ToolDefinition, ToolResult
from tools.registry import ToolRegistry, get_registry

logger = logging.getLogger(__name__)

ERROR_MESSAGES = {
    "not_found": "Tool '{name}' not found",
    "disabled": "Tool '{name}' is currently disabled",
    "timeout": "Tool '{name}' execution timed out after {timeout}s",
    "invalid_args": "Invalid arguments for tool '{name}': {error}",
    "execution": "Tool '{name}' failed: {error}",
}


async def execute_tool(
    tool_call: ToolCall,
    registry: Optional[ToolRegistry] = None,
    timeout: Optional[int] = None,
) -> ToolResult:
    """
    Execute a tool call. Returns ToolResult with result or error.
    """
    reg = registry or get_registry()
    tool = reg.get_tool(tool_call.name)
    if not tool:
        msg = ERROR_MESSAGES["not_found"].format(name=tool_call.name)
        return ToolResult(tool_call_id=tool_call.id, content=msg, success=False, error=msg)
    if not tool.enabled:
        msg = ERROR_MESSAGES["disabled"].format(name=tool_call.name)
        return ToolResult(tool_call_id=tool_call.id, content=msg, success=False, error=msg)

    handler = tool.handler
    if not callable(handler):
        msg = ERROR_MESSAGES["execution"].format(name=tool_call.name, error="Handler not callable")
        return ToolResult(tool_call_id=tool_call.id, content=msg, success=False, error=msg)

    effective_timeout = timeout if timeout is not None else tool.timeout
    args = tool_call.arguments or {}

    try:
        import time
        start = time.perf_counter()
        if asyncio.iscoroutinefunction(handler):
            result = await asyncio.wait_for(handler(**args), timeout=effective_timeout)
        else:
            result = await asyncio.wait_for(
                asyncio.to_thread(handler, **args),
                timeout=effective_timeout,
            )
        duration = time.perf_counter() - start
        logger.info("Tool %s executed in %.2fs", tool_call.name, duration)
    except asyncio.TimeoutError:
        msg = ERROR_MESSAGES["timeout"].format(name=tool_call.name, timeout=effective_timeout)
        logger.warning("Tool %s timed out after %ss", tool_call.name, effective_timeout)
        return ToolResult(tool_call_id=tool_call.id, content=msg, success=False, error=msg)
    except TypeError as e:
        msg = ERROR_MESSAGES["invalid_args"].format(name=tool_call.name, error=str(e))
        logger.warning("Tool %s invalid args: %s", tool_call.name, e)
        return ToolResult(tool_call_id=tool_call.id, content=msg, success=False, error=msg)
    except Exception as e:
        logger.exception("Tool %s failed: %s", tool_call.name, e)
        msg = ERROR_MESSAGES["execution"].format(name=tool_call.name, error=str(e))
        return ToolResult(tool_call_id=tool_call.id, content=msg, success=False, error=msg)

    if isinstance(result, dict):
        import json
        content = json.dumps(result, ensure_ascii=False)
    elif isinstance(result, str):
        content = result
    else:
        content = str(result) if result is not None else ""
    return ToolResult(tool_call_id=tool_call.id, content=content, success=True)


async def execute_tools(
    tool_calls: List[ToolCall],
    registry: Optional[ToolRegistry] = None,
    parallel: bool = False,
) -> List[ToolResult]:
    """Execute multiple tools. parallel=True uses asyncio.gather."""
    reg = registry or get_registry()
    if parallel:
        results = await asyncio.gather(
            *[execute_tool(tc, registry=reg) for tc in tool_calls],
            return_exceptions=True,
        )
        out = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                out.append(ToolResult(
                    tool_call_id=tool_calls[i].id,
                    content=ERROR_MESSAGES["execution"].format(name=tool_calls[i].name, error=str(r)),
                    success=False,
                    error=str(r),
                ))
            else:
                out.append(r)
        return out
    return [await execute_tool(tc, registry=reg) for tc in tool_calls]
