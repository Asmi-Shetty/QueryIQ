
# Responsibility:It validate the SQL query before execution.
#
# Checks performed (in order):
#   1. Not empty
#   2. No destructive keywords (DROP, DELETE, UPDATE, etc.)
#   3. Must start with SELECT(I made it optional commented as of now)
#   4. No multiple statements (semicolon attack)
#   5. No system table access (sqlite_master etc.)
#   6. Reasonable length
#
# Returns a (passed: bool, message: str) tuple.
# If passed=False, message explains exactly why it was blocked.
# The executor must ONLY run queries where passed=True.

import re


# Keywords that modify or destroy data — all blocked
DESTRUCTIVE_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT",
    "ALTER", "TRUNCATE", "CREATE", "REPLACE",
    "ATTACH", "DETACH", "PRAGMA",
]

# SQLite internal tables that should never be queryable by users
SYSTEM_TABLES = ["sqlite_master", "sqlite_sequence", "sqlite_temp_master"]

MAX_QUERY_LENGTH = 2000   # characters — anything longer is suspicious


def check_guardrails(sql: str) -> tuple[bool, str]:
    """
    Runs all validation checks on the SQL string.

    Args:
        sql : the raw SQL string returned by sql_generator.py

    Returns:
        (True, "OK")                    if all checks pass
        (False, "reason message")       if any check fails
    """

    #  Check 1: Not empty 
    if not sql or not sql.strip():
        return False, "No SQL query was generated. Please rephrase your question."

    sql_stripped = sql.strip()

    #  Check 2: Destructive keyword check 
    sql_upper = sql_stripped.upper()
    for keyword in DESTRUCTIVE_KEYWORDS:
        if re.search(rf'\b{keyword}\b', sql_upper):
            return (
                False,
                f"Blocked: '{keyword}' queries are not allowed. "
                f"Only SELECT queries are permitted."
            )

    #  Check 3: Must start with SELECT 
    # first_word = sql_upper.split()[0] if sql_upper.split() else ""
    # if first_word != "SELECT":
    #     return (
    #         False,
    #         f"Blocked: Query must start with SELECT. "
    #         f"Got '{first_word}' instead."
    #     )

    #  Check 4: No multiple statements (semicolon injection) 
    # Allow a trailing semicolon but not mid-query semicolons
    cleaned = sql_stripped.rstrip(";").rstrip()
    if ";" in cleaned:
        return (
            False,
            "Blocked: Multiple SQL statements detected. "
            "Only a single SELECT query is allowed per request."
        )

    # ── Check 5: No system table access ────────────────────────────
    for sys_table in SYSTEM_TABLES:
        if sys_table.lower() in sql_stripped.lower():
            return (
                False,
                f"Blocked: Access to system table '{sys_table}' is not allowed."
            )

    # ── Check 6: Query length limit ────────────────────────────────
    if len(sql_stripped) > MAX_QUERY_LENGTH:
        return (
            False,
            f"Blocked: Query is too long ({len(sql_stripped)} chars). "
            f"Maximum allowed is {MAX_QUERY_LENGTH} characters."
        )

    # All checks passed
    return True, "OK"