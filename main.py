import threading
import itertools
import sys
import argparse
from config import DEBUG , OPENAI_API_KEY
from agent.core import run_agent
from agent.supervisor import run_supervisor

def loading_spinner(stop_event):
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    while not stop_event.is_set():
        sys.stdout.write(f'\rJarvis is thinking... {next(spinner)}')
        sys.stdout.flush()
        threading.Event().wait(0.1)
    sys.stdout.write('\r' + ' ' * 30 + '\r')
    sys.stdout.flush()

def route_request(user_input: str, chat_name: str = "default", project_name: str = None) -> str:
    # use LLM to decide if this needs multi-agent
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage
    from config import ANTHROPIC_API_KEY, LOOP_CHECK_MODEL
    from langchain_openai import ChatOpenAI
    
    router_llm = ChatOpenAI(model=LOOP_CHECK_MODEL, temperature=0, api_key=OPENAI_API_KEY)
    
    response = router_llm.invoke([
        SystemMessage(content="""Decide if this task needs multiple specialist agents or a single agent.
ONLY use multi-agent when ALL of these are true:
- Task has 3 or more clearly distinct phases
- Phases require genuinely different expertise (research vs coding vs writing)
- Task would clearly benefit from parallel execution

For everything else reply 'single'.
Reply with ONLY 'multi' or 'single'.""")
    ])
    
    if response.content.strip().lower() == "multi":
        print(">> routing to multi-agent supervisor")
        return run_supervisor(user_input)
    
    return run_agent(user_input, chat_name, project_name)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chat', default='default', help='chat session name')
    parser.add_argument('--project', default=None, help='project name')
    args = parser.parse_args()

    chat_info = f"[project: {args.project} | chat: {args.chat}]" if args.project else f"[chat: {args.chat}]"
    print(f"Jarvis is online. {chat_info} Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("Jarvis: Shutting down. See you next time.")
            break

        if not DEBUG:
            stop_event = threading.Event()
            spinner_thread = threading.Thread(target=loading_spinner, args=(stop_event,))
            spinner_thread.start()

        response = route_request(user_input, args.chat, args.project)

        if not DEBUG:
            stop_event.set()
            spinner_thread.join()

        print(f"\nJarvis: {response}\n")

if __name__ == "__main__":
    main()