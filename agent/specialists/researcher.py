from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from config import ANTHROPIC_API_KEY, MODEL_NAME, TEMPERATURE
from tools.web_search import web_search
from tools.file_ops import read_file
from tools.notes import read_notes, read_project_notes

RESEARCHER_TOOLS = [web_search, read_file, read_notes, read_project_notes]

researcher_llm = ChatAnthropic(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=ANTHROPIC_API_KEY
).bind_tools(RESEARCHER_TOOLS)

class ResearcherState(TypedDict):
    messages: Annotated[list, operator.add]
    iteration_count: int

def researcher_agent_node(state: ResearcherState) -> ResearcherState:
    response = researcher_llm.invoke(state["messages"])
    return {
        "messages": [response],
        "iteration_count": state["iteration_count"] + 1
    }

def researcher_tools_node(state: ResearcherState) -> ResearcherState:
    tool_calls = state["messages"][-1].tool_calls
    results = []
    for tool_call in tool_calls:
        tool_to_run = next(t for t in RESEARCHER_TOOLS if t.name == tool_call['name'])
        tool_result = tool_to_run.invoke(tool_call['args'])
        results.append(ToolMessage(
            content=tool_result,
            tool_call_id=tool_call['id']
        ))
    return {"messages": results}

def researcher_should_continue(state: ResearcherState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    if state["iteration_count"] >= 5:  # specialists have tighter limits
        return "end"
    return "end"

def build_researcher():
    graph = StateGraph(ResearcherState)
    graph.add_node("agent", researcher_agent_node)
    graph.add_node("tools", researcher_tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        researcher_should_continue,
        {"tools": "tools", "end": END}
    )
    graph.add_edge("tools", "agent")
    return graph.compile()

researcher_graph = build_researcher()

def run_researcher(task: str) -> str:
    """entry point for supervisor to call this specialist"""
    result = researcher_graph.invoke({
        "messages": [
            SystemMessage(content="""You are a research specialist. 
            Your only job is to find accurate, relevant information.
            Be thorough but concise. Return a clear summary of findings."""),
            HumanMessage(content=task)
        ],
        "iteration_count": 0
    })
    return result["messages"][-1].content