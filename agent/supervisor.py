import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from config import ANTHROPIC_API_KEY, MODEL_NAME, TEMPERATURE, MAX_PARALLEL_AGENTS
from agent.agent_factory import create_agent
from tools.web_search import web_search
from tools.calculator import calculator
from tools.file_ops import read_file, write_file
from tools.code_executor import run_python_code
from tools.time_tool import get_current_time
from tools.notes import read_notes, update_notes, read_project_notes, update_project_notes, add_chat_summary

supervisor_llm = ChatAnthropic(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=ANTHROPIC_API_KEY
)

TOOL_REGISTRY = {
    "web_search": web_search,
    "calculator": calculator,
    "read_file": read_file,
    "write_file": write_file,
    "run_python_code": run_python_code,
    "get_current_time": get_current_time,
    "read_notes": read_notes,
    "update_notes": update_notes,
    "read_project_notes": read_project_notes,
    "update_project_notes": update_project_notes,
    "add_chat_summary": add_chat_summary,
}

# rate limiter - max 3 simultaneous API calls
api_semaphore = threading.Semaphore(MAX_PARALLEL_AGENTS)

def rate_limited_run(agent, task_input: str) -> str:
    with api_semaphore:
        return agent(task_input)

def create_task_plan(user_input: str) -> list:
    response = supervisor_llm.invoke([
        SystemMessage(content=f"""You are a task planning supervisor.
        Break the user request into subtasks. For each subtask create a focused agent.
        
        Available tools: {list(TOOL_REGISTRY.keys())}
        
        File storage rules:
        - reports and documents → reports/
        - python scripts and code files → workspace/scripts/
        - data files → workspace/data/
        - never save files to root directory
        
        Return ONLY valid JSON, no explanation, no markdown:
        {{
            "tasks": [
                {{
                    "id": 1,
                    "name": "descriptive_agent_name",
                    "tools": ["tool1", "tool2"],
                    "system_prompt": "You are a specialist in X. Your job is to Y.",
                    "input": "specific task description",
                    "depends_on": []
                }}
            ]
        }}
        
        Rules:
        - assign only tools the agent genuinely needs
        - system_prompt should be focused and specific
        - depends_on contains task ids that must complete first
        - independent tasks have empty depends_on []"""),
        HumanMessage(content=user_input)
    ])

    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    plan = json.loads(content.strip())
    return plan["tasks"]

def execute_plan(tasks: list) -> dict:
    completed = {}
    pending = {t["id"]: t for t in tasks}
    futures = {}

    with ThreadPoolExecutor(max_workers=6) as executor:

        def submit_task(t):
            agent_tools = [TOOL_REGISTRY[name] for name in t["tools"] if name in TOOL_REGISTRY]
            agent = create_agent(tools=agent_tools, system_prompt=t["system_prompt"])
            future = executor.submit(rate_limited_run, agent, t["input"])
            futures[future] = t
            print(f">> spawning agent [{t['name']}] task {t['id']}")

        # submit all independent tasks immediately
        for t in pending.values():
            if not t["depends_on"]:
                submit_task(t)

        # streaming DAG - trigger dependent tasks as soon as dependencies complete
        while futures:
            for future in as_completed(list(futures.keys())):
                task = futures.pop(future)
                result = future.result()
                completed[task["id"]] = {
                    "name": task["name"],
                    "input": task["input"],
                    "result": result
                }
                del pending[task["id"]]
                print(f">> agent [{task['name']}] completed task {task['id']}")

                # immediately check newly unblocked tasks
                newly_ready = [
                    t for t in pending.values()
                    if t["id"] not in [f_task["id"] for f_task in futures.values()]
                    and all(dep in completed for dep in t["depends_on"])
                ]
                for t in newly_ready:
                    submit_task(t)

                break  # restart as_completed with updated futures

    return completed

def synthesize_results(user_input: str, completed: dict) -> str:
    results_text = "\n\n".join([
        f"[{v['name'].upper()} - Task {k}]\nInput: {v['input']}\nOutput: {v['result']}"
        for k, v in completed.items()
    ])

    response = supervisor_llm.invoke([
        SystemMessage(content="""You are a supervisor combining specialist outputs.
        Synthesize all results into a single coherent response for the user.
        Be concise. Don't repeat everything — summarize what was accomplished."""),
        HumanMessage(content=f"Original request: {user_input}\n\nSpecialist results:\n{results_text}")
    ])

    return response.content

def run_supervisor(user_input: str) -> str:
    print(">> supervisor planning tasks...")
    tasks = create_task_plan(user_input)

    for t in tasks:
        print(f"   task {t['id']}: [{t['name']}] tools: {t['tools']} depends_on: {t['depends_on']}")

    print(">> executing task plan...")
    completed = execute_plan(tasks)

    print(">> synthesizing results...")
    return synthesize_results(user_input, completed)