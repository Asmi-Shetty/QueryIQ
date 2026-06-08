# test_agent.py
# Runs all 4 required questions + a multi-turn follow-up to verify memory.

from agent        import run_agent
from chat_history import ChatHistory

history = ChatHistory()   # one shared history = one conversation session

questions = [
    "How many employees are in the Engineering department?",
    "List all projects that are overdue.",
    "Which department has the highest average salary?",
    "Show employees hired after January 2023.",
    "From those employees, who has the highest salary?",   # multi-turn follow-up
]

for i, q in enumerate(questions, 1):
    print(f"\n{'='*60}")
    print(f"Q{i}: {q}")
    print(f"Chat history length: {len(history)} messages")
    print('='*60)

    result = run_agent(q, history)

    if result["error"]:
        print(f"\nError: {result['error']}")
    else:
        print(f"\nExplanation : {result['explanation']}")
        print(f"SQL         :\n{result['sql']}")
        print(f"Rows        : {result['row_count']}  |  Time: {result['exec_time']}s  |  Retries: {result['retries']}")
        if result["dataframe"] is not None and not result["dataframe"].empty:
            print("\nResults:")
            print(result["dataframe"].to_string(index=False))
        else:
            print("(no rows returned)")