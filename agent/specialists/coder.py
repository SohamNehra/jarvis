from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from config import ANTHROPIC_API_KEY, MODEL_NAME, TEMPERATURE
from tools.code_executor import run_python_code
from tools.file_ops import read_file, write_file
from tools.calculator import calculator

CODER_TOOLS = [run_python_code, read_file, write_file, calculator]

coder_llm = ChatAnthropic(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=ANTHROPIC_API_KEY
).bind_tools(CODER_TOOLS)

class CoderState(TypedDict):
    messages: Annotated[list, operator.add]
    iteration_count: int

def coder_agent_node(state: CoderState) -> CoderState:
    response = coder_llm.invoke(state["messages"])
    return {
        "messages": [response],
        "iteration_count": state["iteration_count"] + 1
    }

def coder_tools_node(state: CoderState) -> CoderState:
    tool_calls = state["messages"][-1].tool_calls
    results = []
    for tool_call in tool_calls:
        tool_to_run = next(t for t in CODER_TOOLS if t.name == tool_call['name'])
        tool_result = tool_to_run.invoke(tool_call['args'])
        results.append(ToolMessage(
            content=tool_result,
            tool_call_id=tool_call['id']
        ))
    return {"messages": results}

def coder_should_continue(state: CoderState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    if state["iteration_count"] >= 5:
        return "end"
    return "end"

def build_coder():
    graph = StateGraph(CoderState)
    graph.add_node("agent", coder_agent_node)
    graph.add_node("tools", coder_tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        coder_should_continue,
        {"tools": "tools", "end": END}
    )
    graph.add_edge("tools", "agent")
    return graph.compile()

coder_graph = build_coder()

def run_coder(task: str) -> str:
    """entry point for supervisor to call this specialist"""
    result = coder_graph.invoke({
        "messages": [
            SystemMessage(content="""You are a Python coding specialist.
            Your only job is to write clean, correct, and efficient Python code.
            When asked to solve a problem: think step by step, write the code, execute it to verify it works, and return the final result.
            Prefer simple solutions. Always test your code before returning it.
            If arithmetic is needed, use the calculator tool instead of computing mentally."""),
            HumanMessage(content=task)
        ],
        "iteration_count": 0
    })
    return result["messages"][-1].content
