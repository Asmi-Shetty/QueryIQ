"""
test_full.py
============
Complete test suite for the NL-SQL Agent.

Covers:
  1. ChatHistory  — unit tests
  2. Guardrail    — unit tests (pass + block cases)
  3. SQL Executor — unit tests (valid SQL, bad SQL, empty result)
  4. Agent (E2E)  — 5 real questions via Mistral API

Run:
    python test_full.py
"""

import sys

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

PASS  = "[PASS]"
FAIL  = "[FAIL]"
SEP   = "-" * 60

def section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")

def check(label: str, condition: bool, extra: str = ""):
    status = PASS if condition else FAIL
    msg    = f"  {status}  {label}"
    if extra:
        msg += f"  ({extra})"
    print(msg)
    return condition


# ──────────────────────────────────────────────────────────────────────────────
# 1. ChatHistory Unit Tests
# ──────────────────────────────────────────────────────────────────────────────

section("1. ChatHistory — Unit Tests")

from chat_history import ChatHistory
from langchain_core.messages import HumanMessage, AIMessage

h = ChatHistory()

# 1-A: starts empty
check("Starts with 0 messages", len(h) == 0)
check("get_history() returns empty list", h.get_history() == [])
check("summary() says no history yet", "No conversation history" in h.summary())

# 1-B: add messages
h.add_user_message("Hello!")
check("After add_user_message -> len == 1", len(h) == 1)
check("First message is HumanMessage", isinstance(h.get_history()[0], HumanMessage))

h.add_ai_message("SELECT 1;")
check("After add_ai_message -> len == 2", len(h) == 2)
check("Second message is AIMessage", isinstance(h.get_history()[1], AIMessage))

# 1-C: summary contains both roles
summary = h.summary()
check("summary() contains [User]",      "[User]" in summary)
check("summary() contains [Assistant]", "[Assistant]" in summary)

# 1-D: long message is truncated in summary
h2 = ChatHistory()
h2.add_user_message("A" * 200)
check("Long message truncated to 120 chars + '...'", "..." in h2.summary())

# 1-E: clear
h.clear()
check("After clear() -> len == 0",         len(h) == 0)
check("After clear() -> get_history() []", h.get_history() == [])


# ──────────────────────────────────────────────────────────────────────────────
# 2. Guardrail Unit Tests
# ──────────────────────────────────────────────────────────────────────────────

section("2. Guardrail — Unit Tests")

from guardrail import check_guardrails

# --- Cases that should PASS ---
pass_cases = [
    ("SELECT * FROM employees",                          "plain SELECT"),
    ("SELECT COUNT(*) FROM departments",                 "aggregate"),
    ("SELECT name FROM employees WHERE salary > 80000",  "WHERE clause"),
    ("SELECT e.name, d.name FROM employees e JOIN departments d ON e.department_id = d.id",
                                                         "JOIN query"),
    ("SELECT * FROM employees;",                         "trailing semicolon allowed"),
    ("select * from projects where status = 'active'",   "lowercase select"),
]
for sql, label in pass_cases:
    passed, msg = check_guardrails(sql)
    check(f"PASS expected: {label}", passed, msg)

# --- Cases that should FAIL (blocked) ---
fail_cases = [
    ("",                                                 "empty string",          "empty"),
    ("   ",                                              "whitespace only",        "empty"),
    ("DROP TABLE employees",                             "DROP keyword",           "DROP"),
    ("DELETE FROM employees WHERE id = 1",               "DELETE keyword",         "DELETE"),
    ("UPDATE employees SET salary=0",                    "UPDATE keyword",         "UPDATE"),
    ("INSERT INTO departments VALUES (9,'X','Y',0)",     "INSERT keyword",         "INSERT"),
    ("ALTER TABLE employees ADD COLUMN age INTEGER",     "ALTER keyword",          "ALTER"),
    ("TRUNCATE TABLE salaries",                          "TRUNCATE keyword",       "TRUNCATE"),
    ("PRAGMA table_info(employees)",                     "PRAGMA keyword",         "PRAGMA"),
    ("SELECT * FROM employees; DROP TABLE employees",    "multi-statement attack",  ";"),
    ("SELECT * FROM sqlite_master",                      "system table access",    "sqlite_master"),
    ("SELECT " + "x" * 2001,                            "query too long",         "long"),
]
for sql, label, _ in fail_cases:
    passed, msg = check_guardrails(sql)
    check(f"BLOCK expected: {label}", not passed, msg[:60])


# ──────────────────────────────────────────────────────────────────────────────
# 3. SQL Executor Unit Tests
# ──────────────────────────────────────────────────────────────────────────────

section("3. SQL Executor — Unit Tests")

from sql_executor import execute_sql

# 3-A: valid query returns rows
success, df, exec_time, row_count, error = execute_sql(
    "SELECT * FROM employees LIMIT 5"
)
check("Valid query succeeds",              success)
check("Returns a DataFrame",              df is not None)
check("Row count == 5",                   row_count == 5)
check("exec_time >= 0",                   exec_time >= 0)
check("error is None",                    error is None)
if df is not None:
    check("DataFrame has 'name' column",  "name" in df.columns)

# 3-B: query that returns 0 rows
success2, df2, _, row_count2, _ = execute_sql(
    "SELECT * FROM employees WHERE salary > 9999999"
)
check("Zero-row query still succeeds",    success2)
check("row_count == 0",                   row_count2 == 0)
check("DataFrame is not None",           df2 is not None)
check("DataFrame is empty",              df2.empty)

# 3-C: invalid SQL returns error
success3, df3, _, _, error3 = execute_sql(
    "SELECT * FROM nonexistent_table_xyz"
)
check("Bad SQL returns success=False",   not success3)
check("df is None on failure",           df3 is None)
check("error message is non-empty",      bool(error3))

# 3-D: aggregate queries
success4, df4, _, _, _ = execute_sql(
    "SELECT department_id, COUNT(*) as cnt FROM employees GROUP BY department_id"
)
check("GROUP BY query succeeds",         success4)
check("Has 'cnt' column",               "cnt" in df4.columns if df4 is not None else False)

# 3-E: JOIN query
success5, df5, _, row_count5, _ = execute_sql(
    "SELECT e.name, d.name as dept FROM employees e JOIN departments d ON e.department_id = d.id LIMIT 3"
)
check("JOIN query succeeds",             success5)
check("JOIN has 3 rows",                 row_count5 == 3)
check("Has 'dept' column",              "dept" in df5.columns if df5 is not None else False)

# 3-F: wrong db path
success6, _, _, _, error6 = execute_sql(
    "SELECT 1", db_path="does_not_exist.db"
)
# SQLite creates the file automatically, but the table won't exist
# We test with a bad query on the empty db
success6b, _, _, _, error6b = execute_sql(
    "SELECT * FROM employees", db_path="does_not_exist.db"
)
check("Query on empty/wrong db fails gracefully", not success6b)
check("Error message returned",                   bool(error6b))


# ──────────────────────────────────────────────────────────────────────────────
# 4. Agent End-to-End Tests (calls Mistral API)
# ──────────────────────────────────────────────────────────────────────────────

section("4. Agent — End-to-End Tests (Mistral API)")
print("  Note: These require a valid MISTRAL_API_KEY in .env\n")

from agent        import run_agent
from chat_history import ChatHistory

history = ChatHistory()

e2e_questions = [
    # (question,                                                  description)
    ("How many employees are in the Engineering department?",     "Count by department"),
    ("List all projects that are overdue.",                       "Filter by status"),
    ("Which department has the highest average salary?",          "Aggregate + ORDER BY"),
    ("Show employees hired after January 2023.",                  "Date filter"),
    ("From those employees, who has the highest salary?",         "Multi-turn follow-up"),
]

all_passed = True
for i, (question, desc) in enumerate(e2e_questions, 1):
    print(f"\n  Q{i} [{desc}]")
    print(f"  Question : {question}")
    print(f"  History  : {len(history)} messages so far")

    result = run_agent(question, history)

    if result["error"]:
        check(f"Q{i} succeeded (no error)", False, result["error"][:80])
        all_passed = False
    else:
        ok = check(f"Q{i} succeeded (no error)", True)
        check(f"Q{i} has SQL",                   bool(result["sql"]))
        check(f"Q{i} has explanation",            bool(result["explanation"]))
        check(f"Q{i} exec_time >= 0",             result["exec_time"] >= 0)
        check(f"Q{i} row_count >= 0",             result["row_count"] >= 0)
        check(f"Q{i} dataframe not None",         result["dataframe"] is not None)
        print(f"\n  SQL:\n    {result['sql'].strip()}")
        print(f"  Explanation: {result['explanation'][:100]}")
        print(f"  Rows: {result['row_count']}  |  Time: {result['exec_time']}s  |  Retries: {result['retries']}")
        if result["dataframe"] is not None and not result["dataframe"].empty:
            print(f"\n  Results preview:")
            print(result["dataframe"].head(5).to_string(index=False, max_colwidth=30))

check("All history updated after 5 questions", len(history) == 10)   # 5 Q + 5 A


# ──────────────────────────────────────────────────────────────────────────────
# 5. Guardrail + Executor pipeline test (no LLM needed)
# ──────────────────────────────────────────────────────────────────────────────

section("5. Guardrail -> Executor Pipeline (no LLM)")

pipeline_cases = [
    ("SELECT name, salary FROM employees ORDER BY salary DESC LIMIT 3",  True,  "top 3 earners"),
    ("DELETE FROM employees WHERE id = 1",                               False, "DELETE blocked"),
    ("SELECT * FROM sqlite_master",                                      False, "system table blocked"),
    ("SELECT dept.name, AVG(emp.salary) FROM employees emp "
     "JOIN departments dept ON emp.department_id = dept.id "
     "GROUP BY dept.name ORDER BY AVG(emp.salary) DESC",                 True,  "complex join"),
]

print()
for sql, expect_run, label in pipeline_cases:
    passed, guard_msg = check_guardrails(sql)
    if not passed:
        result_ok = not expect_run   # we expected a block
        check(f"Pipeline '{label}': correctly blocked", result_ok, guard_msg[:60])
    else:
        success, df, _, row_count, err = execute_sql(sql)
        result_ok = success == expect_run
        extra = f"rows={row_count}" if success else f"err={err}"
        check(f"Pipeline '{label}': ran and got results", result_ok, extra)


# ──────────────────────────────────────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────────────────────────────────────

section("Done")
print("  All tests completed. Review any [FAIL] lines above.")
print()
