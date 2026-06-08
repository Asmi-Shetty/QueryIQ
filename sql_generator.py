
# Responsibility: generate SQL from a natural language question using LangChain + Mistral.
#
# Inputs : user question, DB schema string, chat history list
# Outputs: (sql string, explanation string, raw_llm_response string)
#
# This file does NOT validate, execute, or store anything.
# It ONLY talks to the LLM.

import os
import re
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_mistralai import ChatMistralAI

from schema_context import get_schema_context

load_dotenv()


# ─────────────────────────────────────────
# BUILD THE LANGCHAIN PIPELINE (once at import)
# ─────────────────────────────────────────

def _build_chain(schema: str):
    """
    Builds the LangChain pipeline:
      ChatPromptTemplate | ChatMistralAI | StrOutputParser

    The system message contains the DB schema so Mistral always knows
    which tables and columns it can query.

    MessagesPlaceholder injects the full chat history into every call,
    giving Mistral memory of the entire conversation.
    """

    system_prompt = f"""You are an expert SQL assistant for a company SQLite database.
Your ONLY job is to convert natural language questions into valid SQLite SELECT queries.

DATABASE SCHEMA:
{schema}

STRICT RULES:
1. Only write SELECT queries. NEVER write DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, or CREATE.
2. Always respond in EXACTLY this format — no exceptions:

SQL:
```sql
<your SQL query here>
```

EXPLANATION:
<one or two plain-English sentences describing what this query does>

3. Use proper SQLite syntax.
4. Use JOINs when data spans multiple tables.
5. Use table aliases: e = employees, d = departments, p = projects, s = salaries.
6. If the question cannot be answered from the schema, say so clearly — do NOT guess columns.
7. If you are given a previous SQL error, fix the query to avoid that specific error.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])

    llm = ChatMistralAI(
        model="mistral-large-latest",
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0,        # deterministic output 
    )

    parser = StrOutputParser()

    # LangChain pipe operator: prompt → LLM → plain string
    return prompt | llm | parser


# Load schema and build chain once at module import
_schema = get_schema_context()
_chain  = _build_chain(_schema)


# PARSE LLM OUTPUT → SQL + EXPLANATION

def _parse_response(raw: str) -> tuple[str, str]:
    """
    Splits the LLM response into the SQL query and the plain-English explanation.
    Handles both markdown-fenced and bare SQL.
    """
    sql = ""
    explanation = ""

    if "EXPLANATION:" in raw:
        parts = raw.split("EXPLANATION:", 1)
        explanation = parts[1].strip()
        sql_section = parts[0]
    else:
        sql_section = raw
        explanation = "Query generated."

    # Extract SQL from ```sql ... ``` fences
    match = re.search(r"```(?:sql)?\s*(.*?)```", sql_section, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1).strip()
    else:
        # Fallback: grab first SELECT statement
        match2 = re.search(r"(SELECT\b.*)", sql_section, re.DOTALL | re.IGNORECASE)
        sql = match2.group(1).strip() if match2 else sql_section.strip()

    return sql, explanation


# ─────────────────────────────────────────
# PUBLIC FUNCTION
# ─────────────────────────────────────────

def generate_sql(question: str, chat_history: list, error_context: str = "") -> tuple[str, str, str]:
    """
    Calls Mistral via LangChain to generate a SQL query.

    Args:
        question      : user's natural language question
        chat_history  : list of LangChain HumanMessage / AIMessage objects
        error_context : if a previous SQL attempt failed, pass the error here
                        so the LLM can fix the query on retry

    Returns:
        (sql, explanation, raw_llm_response)
    """
    # If we are retrying after an error, append the error to the question
    full_question = question
    if error_context:
        full_question = (
            f"{question}\n\n"
            f"NOTE: Your previous SQL attempt failed with this error:\n{error_context}\n"
            f"Please fix the query and avoid that error."
        )

    raw_response = _chain.invoke({
        "question": full_question,
        "chat_history": chat_history,
    })

    sql, explanation = _parse_response(raw_response)
    return sql, explanation, raw_response