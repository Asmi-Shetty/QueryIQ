# Responsibility: execute a validated SQL query on company.db and return results.
#
# Inputs : sql string (already validated by guardrail.py)
# Outputs: (success: bool, dataframe | None, exec_time, row_count, error_msg | None)
#
# If execution fails (bad SQL the LLM generated despite validation),
# the error message is returned so agent.py can pass it back to
# sql_generator.py for a retry with the error as context.

import sqlite3
import time
import pandas as pd


def execute_sql(sql: str, db_path: str = "company.db") -> tuple[bool, pd.DataFrame | None, float, int, str | None]:
    """
    Runs the SQL query on the SQLite database.

    Args:
        sql     : a SELECT query that has already passed guardrail checks
        db_path : path to the SQLite file (default: company.db)

    Returns a tuple:
        success   (bool)            : True if query ran without error
        dataframe (DataFrame|None)  : results table, or None on failure
        exec_time (float)           : seconds the query took
        row_count (int)             : number of rows returned
        error     (str|None)        : error message if failed, else None
    """
    conn = None
    start = time.time()

    try:
        conn = sqlite3.connect(db_path)

        # Use pandas to run the query returns a clean DataFrame directly
        df = pd.read_sql_query(sql, conn)

        exec_time = round(time.time() - start, 4)
        return True, df, exec_time, len(df), None

    except Exception as e:
        exec_time = round(time.time() - start, 4)
        # Return the raw error string so agent.py can send it back to Mistral
        return False, None, exec_time, 0, str(e)

    finally:
        if conn:
            conn.close()