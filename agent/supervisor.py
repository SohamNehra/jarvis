import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from config import ANTHROPIC_API_KEY, MODEL_NAME, TEMPERATURE
from agent.specialists.researcher import run_researcher
from agent.specialists.coder import run_coder
from agent.specialists.writer import run_writer

supervisor_llm = ChatAnthropic(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=ANTHROPIC_API_KEY
)

SPECIALIST_MAP = {
    "researcher": run_researcher,
    "coder": run_coder,
    "writer": run_writer
}

def create_task_plan(user_input: str) -> list:
    """ask supervisor LLM to break task into subtasks with dependencies"""
    response = supervisor_llm.invoke([
        SystemMessage(content="""You are a task planning supervisor.
        Break the user request into subtasks for specialist agents.
        
        Available specialists:
        - researcher: finds information, searches web, reads files
        - coder: writes and executes Python code, does calculations
        - writer: produces documents, reports, formatted content
        
        Return ONLY valid JSON, no explanation, no markdown:
        {
            "tasks": [
                {
                    "id": 1,
                    "specialist": "researcher",
                    "input": "specific task description",
                    "depends_on": []
                },
                {
                    "id": 2,
                    "specialist": "coder",
                    "input": "specific task description with context about what researcher found",
                    "depends_on": [1]
                }
            ]
        }
        
        Rules:
        - depends_on contains task ids that must complete first
        - independent tasks have empty depends_on []
        - be specific in input descriptions
        - only use researcher/coder/writer as specialist values"""),
        HumanMessage(content=user_input)
    ])
    
    content = response.content.strip()
    # strip markdown code blocks if present
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    
    plan = json.loads(content.strip())
    return plan["tasks"]

def execute_plan(tasks: list) -> dict:
    """execute tasks respecting dependencies, parallel where possible"""
    completed = {}  # task_id → result
    pending = {t["id"]: t for t in tasks}
    
    while pending:
        # find tasks whose dependencies are all completed
        ready = [
            t for t in pending.values()
            if all(dep in completed for dep in t["depends_on"])
        ]
        
        if not ready:
            break  # circular dependency or error
        
        # run all ready tasks in parallel
        with ThreadPoolExecutor(max_workers=len(ready)) as executor:
            futures = {
                executor.submit(
                    SPECIALIST_MAP[t["specialist"]], 
                    t["input"]
                ): t for t in ready
            }
            
            for future in as_completed(futures):
                task = futures[future]
                result = future.result()
                completed[task["id"]] = {
                    "specialist": task["specialist"],
                    "input": task["input"],
                    "result": result
                }
                del pending[task["id"]]
                print(f">> specialist [{task['specialist']}] completed task {task['id']}")
    
    return completed

def synthesize_results(user_input: str, completed: dict) -> str:
    """supervisor combines all specialist outputs into final answer"""
    results_text = "\n\n".join([
        f"[{v['specialist'].upper()} - Task {k}]\nInput: {v['input']}\nOutput: {v['result']}"
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
    """main entry point — replaces run_agent for complex multi-step tasks"""
    print(">> supervisor planning tasks...")
    tasks = create_task_plan(user_input)
    
    for t in tasks:
        print(f"   task {t['id']}: [{t['specialist']}] {t['input'][:60]}... depends_on: {t['depends_on']}")
    
    print(">> executing task plan...")
    completed = execute_plan(tasks)
    
    print(">> synthesizing results...")
    return synthesize_results(user_input, completed)