#It reads company.db and returns schema as a string for the LLM prompt

import sqlite3

def get_schema_context(db_path="company.db"):
    """
    Connects to SQLite and returns a plain-text
    description of all tables, columns, and foreign keys.
    This is injected into the LangChain prompt.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    schema_parts = []

    for table in tables:
        # Get column details
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        col_lines = []
        for col in columns:
            _, col_name, col_type, _, _, is_pk = col
            pk = " (PRIMARY KEY)" if is_pk else ""
            col_lines.append(f"  - {col_name}: {col_type}{pk}")

        # Get foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        fks = cursor.fetchall()
        fk_lines = []
        for fk in fks:
            fk_lines.append(f"  - FOREIGN KEY ({fk[3]}) REFERENCES {fk[2]}({fk[4]})")

        block = f"Table: {table}\nColumns:\n" + "\n".join(col_lines)
        if fk_lines:
            block += "\nForeign Keys:\n" + "\n".join(fk_lines)

        schema_parts.append(block)

    conn.close()
    return "\n\n".join(schema_parts)


if __name__ == "__main__":
    print(get_schema_context())