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

# --- Nodes ---
def agent_node(state: AgentState) -> AgentState:
    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response],
        "iteration_count": state["iteration_count"] + 1
    }

def tools_node(state: AgentState) -> AgentState:
    """runs whatever tools the LLM requested"""
    tool_calls = state["messages"][-1].tool_calls
    results = []

    for tool_call in tool_calls:
        print(f">> running tool: {tool_call['name']} | args: {tool_call['args']}")
        tool_to_run = next(t for t in TOOLS if t.name == tool_call['name'])
        tool_result = tool_to_run.invoke(tool_call['args'])
        results.append(ToolMessage(
            content=tool_result,
            tool_call_id=tool_call['id']
        ))

    return {"messages": results}

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

def graceful_end_node(state: AgentState) -> AgentState:
    response = llm_with_tools.invoke(
        state["messages"] + [HumanMessage(content="You've hit your iteration limit. Summarize what you found so far.")]
    )
    return {"messages": [response]}

# --- Build the graph ---
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("graceful_end", graceful_end_node)

    graph.set_entry_point("agent")

    graph.add_edge("tools", "agent")

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END, "graceful_end": "graceful_end"}
)

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