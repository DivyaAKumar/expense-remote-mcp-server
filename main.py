from fastmcp import FastMCP
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__),"categories.json")
mcp = FastMCP("ExpenseTracker")

@mcp.tool()
def initialize_database():
    """Initialize the expense database table."""
    init_db()
    return {"status": "ok", "message": "Database initialized."}


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(DATABASE_URL)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    amount NUMERIC(12, 2) NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)


@mcp.tool()
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
):
    """Add an expense to the PostgreSQL database."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO expenses
                    (date, amount, category, subcategory, note)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (date, amount, category, subcategory, note)
            )
            expense_id = cur.fetchone()[0]

    return {"status": "ok", "id": expense_id}


@mcp.tool()
def list_expenses(start_date, end_date):
    """List all expenses from the PostgreSQL database within an inclusive date range."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN %s AND %s
                ORDER BY id ASC
            """,
            (start_date,end_date)
            )

            columns = []

            for desc in cur.description:
                columns.append(desc.name)

            expenses = []
            rows = cur.fetchall()
            for row in rows:
                expense = dict(zip(columns, row))
                expenses.append(expense)

            return expenses

@mcp.tool()
def summarize(start_date, end_date, category=None):
    '''Summarize expenses by category within an inclusive date range'''
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = (
                """
                SELECT category, SUM(amount) AS total_amount
                FROM expenses
                WHERE date BETWEEN %s and %s
                """
            )
            params = [start_date, end_date]
            if category:
                query+=" AND category = %s"
                params.append(category)

            query+=" GROUP BY category ORDER BY category ASC"

            c = cur.execute(query,params)
            cols = [d[0] for d in c.description]
            return [dict(zip(cols,r)) for r in c.fetchall()]


@mcp.tool()
def edit_expense(
    expense_id: int,
    date: str | None = None,
    amount: float | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    note: str | None = None
):
    """Edit an existing expense using its ID. Only provided fields are updated."""

    updates = {
        "date": date,
        "amount": amount,
        "category": category,
        "subcategory": subcategory,
        "note": note
    }

    updates = {
        field: value
        for field, value in updates.items()
        if value is not None
    }

    if not updates:
        return {"status": "error", "message": "No fields provided to update."}

    set_clause = ", ".join(
        f"{field} = %s" for field in updates
    )
    values = list(updates.values())
    values.append(expense_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE expenses
                SET {set_clause}
                WHERE id = %s
                RETURNING id
                """,
                values
            )
            result = cur.fetchone()

    if result is None:
        return {
            "status": "not_found",
            "message": f"No expense found with ID {expense_id}."
        }

    return {"status": "ok", "id": result[0], "updated_fields": list(updates.keys())}


@mcp.tool()
def delete_expense(expense_id: int):
    """Delete an expense from the database using its ID."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM expenses
                WHERE id = %s
                RETURNING id
                """,
                (expense_id,)
            )
            result = cur.fetchone()

    if result is None:
        return {
            "status": "not_found",
            "message": f"No expense found with ID {expense_id}."
        }

    return {
        "status": "ok",
        "message": f"Expense {result[0]} deleted successfully.",
        "id": result[0]
    }


@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    #read fresh each time so you can edit without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()

# Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000) #streamable http
    #mcp.run(default transport - stdio)
 