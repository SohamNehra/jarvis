from agent.core import run_agent

def main():
    print("Jarvis is online. Type 'exit' to quit.\n")
    
    while True:
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == "exit":
            print("Jarvis: Shutting down. See you next time.")
            break
        
        response = run_agent(user_input)
        print(f"\nJarvis: {response}\n")

if __name__ == "__main__":
    main()