from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from config import OPENAI_API_KEY, MODEL_NAME, TEMPERATURE
from tools.web_search import web_search

llm = ChatOpenAI(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=OPENAI_API_KEY
)

llm_with_tools = llm.bind_tools([web_search])

messages = [
    SystemMessage(content="You are Jarvis, a helpful personal AI assistant."),
    HumanMessage(content="Search for what LangChain is and then search for what LangGraph is, then tell me both.")
]

# agent loop
while True:
    response = llm_with_tools.invoke(messages)
    messages.append(response)

    if response.tool_calls:
        for tool_call in response.tool_calls:
            print(f">> running tool: {tool_call['name']} | args: {tool_call['args']}")

            tool_result = web_search.invoke(tool_call['args'])

            messages.append(ToolMessage(
                content=tool_result,
                tool_call_id=tool_call['id']
            ))
    else:
        # no tool calls = LLM has final answer
        print("\nJarvis:", response.content)
        break