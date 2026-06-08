# Orchestrator — ties all modules together.
#
# Flow per question:
#   1. Load chat history
#   2. sql_generator.py  → generate SQL from question + history
#   3. guardrail.py      → validate the SQL
#      └─ FAIL           → return friendly error message immediately
#   4. sql_executor.py   → run the SQL on company.db
#      └─ FAIL           → retry sql_generator.py with error (up to MAX_RETRIES)
#      └─ still FAIL     → return friendly error message
#   5. Save question + LLM response to chat history
#   6. Return full result dict

from sql_generator  import generate_sql
from guardrail      import check_guardrails
from sql_executor   import execute_sql
from chat_history   import ChatHistory

MAX_RETRIES = 2   # how many times to ask the LLM to fix a broken query


def run_agent(question: str, history: ChatHistory) -> dict:
    """
    Main entry point called by app.py or test_agent.py.

    Args:
        question : natural language question from the user
        history  : ChatHistory instance (shared across turns for memory)

    Returns a dict:
        sql         (str)            : the final SQL query used
        explanation (str)            : plain-English explanation from LLM
        dataframe   (DataFrame|None) : query results
        exec_time   (float)          : DB execution time in seconds
        row_count   (int)            : number of rows returned
        error       (str|None)       : error message, or None on success
        retries     (int)            : how many LLM retries were needed
    """

    error_context = ""    # error from last failed execution attempt
    last_sql = ""
    last_explanation = ""
    last_raw_response = ""

    for attempt in range(1 + MAX_RETRIES):

        #  Step 1: Generate SQL 
        try:
            sql, explanation, raw_response = generate_sql(
                question      = question,
                chat_history  = history.get_history(),
                error_context = error_context,      # empty on first attempt
            )
        except Exception as e:
            return _error_result(f"LLM call failed: {str(e)}")

        last_sql          = sql
        last_explanation  = explanation
        last_raw_response = raw_response

        #  Step 2: Guardrail validation 
        passed, guard_message = check_guardrails(sql)

        if not passed:
            # Guardrail failure is final — do NOT retry (it's a safety issue)
            return _error_result(guard_message, sql=sql)

        #  Step 3: Execute SQL 
        success, df, exec_time, row_count, exec_error = execute_sql(sql)

        if success:
            # Save to chat history only on success
            history.add_user_message(question)
            history.add_ai_message(raw_response)

            return {
                "sql":         sql,
                "explanation": explanation,
                "dataframe":   df,
                "exec_time":   exec_time,
                "row_count":   row_count,
                "error":       None,
                "retries":     attempt,
            }

        # Execution failed — pass error back to LLM on next loop iteration
        error_context = exec_error
        print(f"  [Retry {attempt + 1}/{MAX_RETRIES}] SQL failed: {exec_error}")

    # All retries exhausted
    return _error_result(
        f"Query failed after {MAX_RETRIES} retries. Last error: {error_context}",
        sql=last_sql,
    )


def _error_result(message: str, sql: str = "") -> dict:
    """Helper to build a consistent error response dict."""
    return {
        "sql":         sql,
        "explanation": "",
        "dataframe":   None,
        "exec_time":   0,
        "row_count":   0,
        "error":       message,
        "retries":     0,
    }