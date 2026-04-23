from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from config import OPENAI_API_KEY, MODEL_NAME, TEMPERATURE
from tools.web_search import web_search
from tools.calculator import calculator
from tools.time_tool import get_current_time
from memory.memory import save_history, load_history

TOOLS = [web_search, calculator, get_current_time]

llm = ChatOpenAI(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=OPENAI_API_KEY
)

llm_with_tools = llm.bind_tools(TOOLS)

def run_agent(user_input: str) -> str:
    # load previous conversation from disk
    history = load_history()

    messages = [
        SystemMessage(content="You are Jarvis, a helpful personal AI assistant."),
        *history,  # inject previous conversation
        HumanMessage(content=user_input)
    ]

    while True:
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if response.tool_calls:
            for tool_call in response.tool_calls:
                print(f">> running tool: {tool_call['name']} | args: {tool_call['args']}")
                tool_to_run = next(t for t in TOOLS if t.name == tool_call['name'])
                tool_result = tool_to_run.invoke(tool_call['args'])
                messages.append(ToolMessage(
                    content=tool_result,
                    tool_call_id=tool_call['id']
                ))
        else:
            # save conversation to disk before returning
            save_history(messages)
            return response.content