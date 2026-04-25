from langchain_anthropic import ChatAnthropic 
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from config import ANTHROPIC_API_KEY, LOOP_CHECK_MODEL, MODEL_NAME, OPENAI_API_KEY, TEMPERATURE , DEBUG
from tools.web_search import web_search
from tools.calculator import calculator
from tools.time_tool import get_current_time
from tools.file_ops import read_file, write_file
from memory.memory import save_history, load_history
from langgraph.types import Send
import time
from langchain_openai import ChatOpenAI
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

TOOLS = [web_search, calculator, get_current_time, read_file, write_file]
AGENT_TIMEOUT_SECONDS = 60

llm = ChatAnthropic(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=ANTHROPIC_API_KEY 
)
loop_check_llm = ChatOpenAI(
    model=LOOP_CHECK_MODEL,
    temperature=0,
    api_key=OPENAI_API_KEY
)

llm_with_tools = llm.bind_tools(TOOLS)

# --- State ---
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    iteration_count: int
    current_tool_call: dict
    tool_call_history: Annotated[list, operator.add]

# --- Nodes ---
def agent_node(state: AgentState) -> AgentState:
    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response],
        "iteration_count": state["iteration_count"] + 1
    }

def execute_single_tool(state: AgentState) -> AgentState:
    tool_call = state["current_tool_call"]
    
    if DEBUG:
        start = time.time()
        print(f">> START tool: {tool_call['name']} | thread time: {start:.3f}")
    
    tool_to_run = next(t for t in TOOLS if t.name == tool_call['name'])
    tool_result = tool_to_run.invoke(tool_call['args'])
    
    if DEBUG:
        end = time.time()
        print(f">> END tool: {tool_call['name']} | took: {end - start:.3f}s")
    
    return {"messages": [ToolMessage(
        content=tool_result,
        tool_call_id=tool_call['id']
    )],
    "tool_call_history": [{"name": tool_call['name'], "args": tool_call['args']}]
    }

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

def check_loop(tool_call_history: list) -> bool:
    """uses cheap LLM to detect if agent is stuck in a loop"""
    
    history_text = "\n".join([
        f"- {t['name']}: {t['args']}" 
        for t in tool_call_history
    ])
    
    response = loop_check_llm.invoke([
        SystemMessage(content="""You are a loop detector for an AI agent. 
        Analyze the last tool calls and decide if the agent is stuck repeating 
        itself or genuinely making progress. Reply with ONLY 'stuck' or 'progress'."""),
        HumanMessage(content=f"Last tool calls:\n{history_text}\n\nStuck or progress?")
    ])
    
    return response.content.strip().lower() == "stuck"

# --- Edge condition ---
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    
    if last_message.tool_calls:
        return "tools"
    
    if state["iteration_count"] >= 10:
        return "graceful_end"
    
    tool_history = state.get("tool_call_history", [])
    if len(tool_history) >= 4:  # at least 4 tool calls have happened
        if check_loop(tool_history[-4:]):
            print(">> loop detected, asking user for guidance")
            return "graceful_end"
    
    return "end"

def route_tools_node(state: AgentState) -> AgentState:
    """pass-through node - just triggers the parallel routing edge"""
    return {}

def graceful_end_node(state: AgentState) -> AgentState:
    assessment = llm.invoke(
        state["messages"] + [HumanMessage(content="""
        You are stuck or have hit a limit. Do the following:
        1. Briefly summarize what you have accomplished so far
        2. Explain exactly where you are stuck or what you need
        3. Ask the user ONE specific question that would help you continue
        Format: 
        PROGRESS: [what you did]
        STUCK: [what the problem is]
        QUESTION: [your specific question for the user]
        """)]
    )
    
    print(f"\nJarvis: {assessment.content}\n")
    
    user_response = input("You: ").strip()
    
    # handle exit inside graceful node
    if user_response.lower() == "exit":
        print("Jarvis: Shutting down. See you next time.")
        import sys
        sys.exit(0)
    
    if not user_response:
        user_response = "Please summarize what you found and stop."
    
    return {
        "messages": [assessment, HumanMessage(content=user_response)],
        "iteration_count": 0,
        "tool_call_history": []
    }

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
    graph.add_edge("graceful_end", "agent")

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
        "iteration_count": 0,
        "tool_call_history": []
    }

    def invoke():
        return jarvis.invoke(initial_state)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(invoke)
        try:
            final_state = future.result(timeout=AGENT_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            print(f">> timeout: agent exceeded {AGENT_TIMEOUT_SECONDS}s")
            return "I ran out of time completing that task. Please try a simpler request or break it into smaller parts."

    final_message = final_state["messages"][-1]
    save_history(final_state["messages"])
    return final_message.content