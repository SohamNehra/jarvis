from langchain_anthropic import ChatAnthropic 
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from config import ANTHROPIC_API_KEY, MODEL_NAME, TEMPERATURE
from tools.web_search import web_search
from tools.calculator import calculator
from tools.time_tool import get_current_time
from memory.memory import save_history, load_history
from langgraph.types import Send
import time

TOOLS = [web_search, calculator, get_current_time]

llm = ChatAnthropic(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=ANTHROPIC_API_KEY 
)

llm_with_tools = llm.bind_tools(TOOLS)

# --- State ---
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    iteration_count: int
    current_tool_call: dict  

# --- Nodes ---
def agent_node(state: AgentState) -> AgentState:
    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response],
        "iteration_count": state["iteration_count"] + 1
    }

def execute_single_tool(state: AgentState) -> AgentState:
    tool_call = state["current_tool_call"]
    
    start = time.time()
    print(f">> START tool: {tool_call['name']} | thread time: {start:.3f}")
    
    tool_to_run = next(t for t in TOOLS if t.name == tool_call['name'])
    tool_result = tool_to_run.invoke(tool_call['args'])
    
    end = time.time()
    print(f">> END tool: {tool_call['name']} | took: {end - start:.3f}s")
    
    return {"messages": [ToolMessage(
        content=tool_result,
        tool_call_id=tool_call['id']
    )]}

def route_tool_calls(state: AgentState) -> list:
    tool_calls = state["messages"][-1].tool_calls
    return [
        Send("execute_tool", {
            "current_tool_call": tool_call,
            "messages": [],        # empty - executor only needs the tool call
            "iteration_count": state["iteration_count"]
        })
        for tool_call in tool_calls
    ]

# --- Edge condition ---
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    
    if last_message.tool_calls:
        # tools pending - must run them first, no shortcuts
        return "tools"
    
    # only check iteration limit when no tools are pending
    if state["iteration_count"] >= 10:
        return "graceful_end"
    
    return "end"

def route_tools_node(state: AgentState) -> AgentState:
    """pass-through node - just triggers the parallel routing edge"""
    return {}

def graceful_end_node(state: AgentState) -> AgentState:
    response = llm_with_tools.invoke(
        state["messages"] + [HumanMessage(content="You've hit your iteration limit. Summarize what you found so far.")]
    )
    return {"messages": [response]}

# --- Build the graph ---
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("execute_tool", execute_single_tool)  # replaces tools_node
    graph.add_node("graceful_end", graceful_end_node)
    graph.add_node("route_tools", route_tools_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "route_tools", "end": END, "graceful_end": "graceful_end"}
    )
    
    # this edge dynamically spawns parallel Send instances
    graph.add_conditional_edges(
        "route_tools",
        route_tool_calls,
        ["execute_tool"]  # tells graph these Sends route to execute_tool
    )

    graph.add_edge("execute_tool", "agent")
    graph.add_edge("graceful_end", END)

    return graph.compile()

jarvis = build_graph()

def run_agent(user_input: str) -> str:
    history = load_history()

    initial_state = {
        "messages": [
            SystemMessage(content="You are Jarvis, a helpful personal AI assistant."),
            *history,
            HumanMessage(content=user_input)
        ],
        "iteration_count": 0
    }

    final_state = jarvis.invoke(initial_state)
    final_message = final_state["messages"][-1]

    save_history(final_state["messages"])
    return final_message.content