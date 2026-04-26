from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.types import Send
from typing import TypedDict, Annotated
import operator
from config import ANTHROPIC_API_KEY, MODEL_NAME, TEMPERATURE

def create_agent(tools: list, system_prompt: str, max_iterations: int = 5) -> callable:
    
    llm = ChatAnthropic(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        api_key=ANTHROPIC_API_KEY
    ).bind_tools(tools)

    class AgentState(TypedDict):
        messages: Annotated[list, operator.add]
        iteration_count: int
        current_tool_call: dict

    def agent_node(state: AgentState) -> AgentState:
        response = llm.invoke(state["messages"])
        return {
            "messages": [response],
            "iteration_count": state["iteration_count"] + 1
        }

    def execute_single_tool(state: AgentState) -> AgentState:
        """executes ONE tool - runs in parallel with other tool instances"""
        tool_call = state["current_tool_call"]
        tool_to_run = next(t for t in tools if t.name == tool_call['name'])
        tool_result = tool_to_run.invoke(tool_call['args'])
        return {"messages": [ToolMessage(
            content=tool_result,
            tool_call_id=tool_call['id']
        )]}

    def route_tool_calls(state: AgentState) -> list:
        """spawns parallel Send instances for each tool call"""
        tool_calls = state["messages"][-1].tool_calls
        return [
            Send("execute_tool", {
                "current_tool_call": tool_call,
                "messages": [],
                "iteration_count": state["iteration_count"]
            })
            for tool_call in tool_calls
        ]

    def route_tools_node(state: AgentState) -> AgentState:
        """pass-through node for parallel routing edge"""
        return {}

    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        if state["iteration_count"] >= max_iterations:
            return "end"
        return "end"

    # build graph
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("route_tools", route_tools_node)
    graph.add_node("execute_tool", execute_single_tool)
    graph.set_entry_point("agent")
    
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "route_tools", "end": END}
    )
    graph.add_conditional_edges(
        "route_tools",
        route_tool_calls,
        ["execute_tool"]
    )
    graph.add_edge("execute_tool", "agent")
    
    compiled = graph.compile()

    def run(task: str) -> str:
        result = compiled.invoke({
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=task)
            ],
            "iteration_count": 0,
            "current_tool_call": {}
        })
        return result["messages"][-1].content

    return run