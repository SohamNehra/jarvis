from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from config import ANTHROPIC_API_KEY, MODEL_NAME, TEMPERATURE
from tools.file_ops import read_file, write_file
from tools.notes import read_notes, read_project_notes

WRITER_TOOLS = [read_file, write_file, read_notes, read_project_notes]

writer_llm = ChatAnthropic(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=ANTHROPIC_API_KEY
).bind_tools(WRITER_TOOLS)

class WriterState(TypedDict):
    messages: Annotated[list, operator.add]
    iteration_count: int

def writer_agent_node(state: WriterState) -> WriterState:
    response = writer_llm.invoke(state["messages"])
    return {
        "messages": [response],
        "iteration_count": state["iteration_count"] + 1
    }

def writer_tools_node(state: WriterState) -> WriterState:
    tool_calls = state["messages"][-1].tool_calls
    results = []
    for tool_call in tool_calls:
        tool_to_run = next(t for t in WRITER_TOOLS if t.name == tool_call['name'])
        tool_result = tool_to_run.invoke(tool_call['args'])
        results.append(ToolMessage(
            content=tool_result,
            tool_call_id=tool_call['id']
        ))
    return {"messages": results}

def writer_should_continue(state: WriterState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    if state["iteration_count"] >= 5:
        return "end"
    return "end"

def build_writer():
    graph = StateGraph(WriterState)
    graph.add_node("agent", writer_agent_node)
    graph.add_node("tools", writer_tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        writer_should_continue,
        {"tools": "tools", "end": END}
    )
    graph.add_edge("tools", "agent")
    return graph.compile()

writer_graph = build_writer()

def run_writer(task: str) -> str:
    """entry point for supervisor to call this specialist"""
    result = writer_graph.invoke({
        "messages": [
            SystemMessage(content="""You are a writing specialist.
            Your only job is to produce clear, well-structured, and polished written content.
            When given a task: read any relevant context files or notes first, then write content that is concise and purposeful.
            Adapt your tone and format to the request — technical docs, summaries, emails, or prose.
            Save output to a file when the task asks for a deliverable."""),
            HumanMessage(content=task)
        ],
        "iteration_count": 0
    })
    return result["messages"][-1].content
