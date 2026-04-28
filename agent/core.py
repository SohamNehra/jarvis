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
from tools.notes import read_project_notes, set_project, update_notes, read_notes, add_chat_summary, update_project_notes
from memory.memory import load_project_notes, save_history, load_history
from langgraph.types import Send
import time
from langchain_openai import ChatOpenAI
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from tools.code_executor import run_python_code
import json

TOOLS = [web_search, calculator, get_current_time, read_file, write_file, update_notes, read_notes, add_chat_summary, run_python_code, update_project_notes, read_project_notes]
AGENT_TIMEOUT_SECONDS = 300

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


def should_continue_api(state: AgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    if state["iteration_count"] >= 10:
        return "end"
    tool_history = state.get("tool_call_history", [])
    if len(tool_history) >= 4 and check_loop(tool_history[-4:]):
        return "end"
    return "end"


def build_api_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("execute_tool", execute_single_tool)
    graph.add_node("route_tools", route_tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue_api, {"tools": "route_tools", "end": END})
    graph.add_conditional_edges("route_tools", route_tool_calls, ["execute_tool"])
    graph.add_edge("execute_tool", "agent")
    return graph.compile()


jarvis_api = build_api_graph()


def run_agent_streaming(user_input: str, chat_name: str, project_name, event_queue) -> None:
    """Runs the agent via jarvis_api.stream() and puts typed events into event_queue.
    Sentinel None is always the last item. event types: tool_start, tool_end, response, error."""
    history = load_history(chat_name, project_name)
    set_project(project_name)

    system_content = "You are Jarvis, a helpful personal AI assistant.\n"
    system_content += """
    Notes system:
    - update_notes / read_notes → YOUR personal profile (name, preferences, background)
    - update_project_notes / read_project_notes → current PROJECT context (goals, decisions, technical details)
    - add_chat_summary → log what was discussed
    Always use project notes for project-specific information when in a project."""

    if project_name:
        project_notes = load_project_notes(project_name)
        if project_notes:
            system_content += f"\n\nProject context ({project_name}):\n{project_notes}"

    initial_state = {
        "messages": [SystemMessage(content=system_content), *history, HumanMessage(content=user_input)],
        "iteration_count": 0,
        "tool_call_history": [],
    }

    all_messages = list(initial_state["messages"])
    pending_starts: dict = {}  # tool_call_id -> start_time

    try:
        for update in jarvis_api.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in update.items():
                new_msgs = node_output.get("messages", [])
                all_messages.extend(new_msgs)

                if node_name == "agent":
                    for msg in new_msgs:
                        for tc in getattr(msg, "tool_calls", []):
                            pending_starts[tc["id"]] = time.time()
                            event_queue.put({"type": "tool_start", "tool": tc["name"], "args": tc["args"]})

                elif node_name == "execute_tool":
                    history_new = node_output.get("tool_call_history", [])
                    tool_name = history_new[0]["name"] if history_new else "unknown"
                    for msg in new_msgs:
                        tc_id = getattr(msg, "tool_call_id", None)
                        if tc_id:
                            start = pending_starts.pop(tc_id, None)
                            took = round(time.time() - start, 2) if start else 0
                            event_queue.put({"type": "tool_end", "tool": tool_name, "took": took})

        final_response = ""
        for msg in reversed(all_messages):
            content = getattr(msg, "content", "")
            if isinstance(content, str) and content.strip() and not getattr(msg, "tool_calls", None):
                final_response = content
                break

        save_history(all_messages, chat_name, project_name)
        event_queue.put({"type": "response", "content": final_response})

    except Exception as e:
        event_queue.put({"type": "error", "message": str(e)})

    finally:
        event_queue.put(None)


def run_agent(user_input: str, chat_name: str = "default", project_name: str = None) -> str:
    history = load_history(chat_name, project_name)
    set_project(project_name)
    # build system prompt with project context if available
    system_content = "You are Jarvis, a helpful personal AI assistant.\n"
    system_content += """
    Notes system:
    - update_notes / read_notes → YOUR personal profile (name, preferences, background)
    - update_project_notes / read_project_notes → current PROJECT context (goals, decisions, technical details)
    - add_chat_summary → log what was discussed
    Always use project notes for project-specific information when in a project."""
    
    if project_name:
        project_notes = load_project_notes(project_name)
        if project_notes:
            system_content += f"\n\nProject context ({project_name}):\n{project_notes}"

    initial_state = {
        "messages": [
            SystemMessage(content=system_content),
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
            print(f">> timeout: single agent exceeded {AGENT_TIMEOUT_SECONDS}s, escalating to supervisor...")
            # import here to avoid circular imports
            from agent.supervisor import run_supervisor
            return run_supervisor(user_input)

    final_message = final_state["messages"][-1]
    save_history(final_state["messages"], chat_name, project_name)
    return final_message.content