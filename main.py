import threading
import itertools
import sys
from config import DEBUG
from agent.core import run_agent

def loading_spinner(stop_event):
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    while not stop_event.is_set():
        sys.stdout.write(f'\rJarvis is thinking... {next(spinner)}')
        sys.stdout.flush()
        threading.Event().wait(0.1)
    sys.stdout.write('\r' + ' ' * 30 + '\r')  # clear the line
    sys.stdout.flush()

def main():
    print("Jarvis is online. Type 'exit' to quit.\n")
    
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

        response = run_agent(user_input)

        if not DEBUG:
            stop_event.set()
            spinner_thread.join()
        
        print(f"\nJarvis: {response}\n")

if __name__ == "__main__":
    main()