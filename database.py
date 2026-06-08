# Creates the SQLite database with 4 tables and fills them with dummy data

import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()



# 1. CONNECT (creates company.db file)

conn = sqlite3.connect("company.db")
cursor = conn.cursor()

# Enable foreign key support in SQLite
cursor.execute("PRAGMA foreign_keys = ON")


# 2. DROP OLD TABLES (so that we can re-run the code safely)

cursor.execute("DROP TABLE IF EXISTS projects")
cursor.execute("DROP TABLE IF EXISTS employees")
cursor.execute("DROP TABLE IF EXISTS departments")
cursor.execute("DROP TABLE IF EXISTS salaries")


# 3. CREATE TABLES

# Table 1: departments
cursor.execute("""
CREATE TABLE departments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    location    TEXT NOT NULL,
    budget      REAL NOT NULL
)
""")

# Table 2: employees
cursor.execute("""
CREATE TABLE employees (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    department_id   INTEGER NOT NULL,
    salary          REAL NOT NULL,
    hire_date       TEXT NOT NULL,
    email           TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id)
)
""")

# Table 3: projects
cursor.execute("""
CREATE TABLE projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    employee_id     INTEGER NOT NULL,
    status          TEXT NOT NULL,      -- 'active', 'completed', 'overdue'
    deadline        TEXT NOT NULL,
    budget          REAL NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
)
""")


# Table 4: salaries (bonus/payment history per employee)
cursor.execute("""
CREATE TABLE salaries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL,
    month           TEXT NOT NULL,      -- e.g. '2024-01'
    amount          REAL NOT NULL,
    bonus           REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
)
""")

print("Tables created successfully.")



# 4. SEED: DEPARTMENTS (8 rows)

department_data = [
    ("Engineering",     "New York",     1500000),
    ("Marketing",       "Los Angeles",   800000),
    ("Sales",           "Chicago",       950000),
    ("HR",              "Houston",       600000),
    ("Finance",         "San Francisco", 1100000),
    ("Design",          "Austin",        700000),
    ("Operations",      "Seattle",       850000),
    ("Data Science",    "Boston",       1200000),
]
cursor.executemany(
    "INSERT INTO departments (name, location, budget) VALUES (?, ?, ?)",
    department_data
)
print("Departments seeded.")



# 5. SEED: EMPLOYEES (20 rows)
 
random.seed(42)
Faker.seed(42)

# Realistic salary ranges per department
salary_ranges = {
    1: (90000, 160000),   # Engineering
    2: (55000, 90000),    # Marketing
    3: (50000, 95000),    # Sales
    4: (50000, 75000),    # HR
    5: (80000, 130000),   # Finance
    6: (60000, 100000),   # Design
    7: (55000, 85000),    # Operations
    8: (95000, 170000),   # Data Science
}

employees_inserted = []
for i in range(20):
    dept_id   = random.randint(1, 8)
    sal_min, sal_max = salary_ranges[dept_id]
    salary    = round(random.uniform(sal_min, sal_max), 2)
    # hire dates spread from 2019 to 2024
    hire_date = fake.date_between(start_date="-6y", end_date="today").strftime("%Y-%m-%d")
    name      = fake.name()
    email     = fake.unique.email()

    cursor.execute(
        "INSERT INTO employees (name, department_id, salary, hire_date, email) VALUES (?, ?, ?, ?, ?)",
        (name, dept_id, salary, hire_date, email)
    )
    employees_inserted.append(cursor.lastrowid)

print("Employees seeded.")



# 6. SEED: PROJECTS (20 rows)

project_names = [
    "Website Redesign", "Data Pipeline", "Mobile App", "CRM Integration",
    "Sales Dashboard", "HR Portal", "Budget Tracker", "Cloud Migration",
    "AI Chatbot", "Security Audit", "Product Launch", "API Gateway",
    "Customer Portal", "Payroll System", "Analytics Engine", "DevOps Setup",
    "Brand Refresh", "Inventory System", "Training Platform", "Compliance Tool"
]
statuses = ["active", "completed", "overdue"]

today = datetime.today()

for i, proj_name in enumerate(project_names):
    emp_id = random.choice(employees_inserted)

    # Mix deadlines: some past (overdue), some future (active), some recent (completed)
    if i % 3 == 0:
        status   = "overdue"
        deadline = (today - timedelta(days=random.randint(10, 120))).strftime("%Y-%m-%d")
    elif i % 3 == 1:
        status   = "active"
        deadline = (today + timedelta(days=random.randint(10, 180))).strftime("%Y-%m-%d")
    else:
        status   = "completed"
        deadline = (today - timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d")

    budget = round(random.uniform(20000, 300000), 2)

    cursor.execute(
        "INSERT INTO projects (name, employee_id, status, deadline, budget) VALUES (?, ?, ?, ?, ?)",
        (proj_name, emp_id, status, deadline, budget)
    )

print("Projects seeded.")

 
# 7. SEED: SALARIES (last 6 months per employee)

for emp_id in employees_inserted:
    # Fetch that employee's base salary
    cursor.execute("SELECT salary FROM employees WHERE id = ?", (emp_id,))
    base = cursor.fetchone()[0]
    monthly = round(base / 12, 2)

    for month_offset in range(6):
        month_date = today.replace(day=1) - timedelta(days=30 * month_offset)
        month_str  = month_date.strftime("%Y-%m")
        bonus      = round(random.uniform(0, 5000), 2) if random.random() > 0.6 else 0.0

        cursor.execute(
            "INSERT INTO salaries (employee_id, month, amount, bonus) VALUES (?, ?, ?, ?)",
            (emp_id, month_str, monthly, bonus)
        )

print("Salary history seeded.")



# 8. COMMIT & VERIFY


conn.commit()

print("\n📊 Row counts:")
for table in ["departments", "employees", "projects", "salaries"]:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"   {table:<15} → {count} rows")

# Preview of each table
print("\n Sample data preview:")

print("\n  departments:")
for row in cursor.execute("SELECT * FROM departments LIMIT 3"):
    print("  ", row)

print("\n  employees:")
for row in cursor.execute("SELECT id, name, department_id, salary, hire_date FROM employees LIMIT 3"):
    print("  ", row)

print("\n  projects:")
for row in cursor.execute("SELECT * FROM projects LIMIT 3"):
    print("  ", row)

print("\n  salaries:")
for row in cursor.execute("SELECT * FROM salaries LIMIT 3"):
    print("  ", row)

conn.close()
print("\n company.db is ready!")