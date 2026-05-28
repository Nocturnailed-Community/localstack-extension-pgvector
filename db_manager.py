"""
Database Manager for pgvector LocalStack Extension.
Provides full CRUD operations for tables, rows, and vector search.
"""

import json
import logging

LOG = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL connections and provides methods for
    table management, data CRUD, and vector similarity search.
    """

    def __init__(self, host="localhost", port=5432, user="postgres", password="postgres", dbname="postgres"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.dbname = dbname
        self._conn = None

    def _get_connection(self):
        """Lazily create and return a database connection."""
        if self._conn is None or self._conn.closed:
            try:
                import psycopg2
                self._conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    dbname=self.dbname
                )
                self._conn.autocommit = True
                LOG.info(f"Connected to PostgreSQL at {self.host}:{self.port}/{self.dbname}")
            except Exception as e:
                LOG.error(f"Failed to connect to PostgreSQL: {e}")
                raise
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            LOG.info("Database connection closed.")

    # ─── Table Operations ─────────────────────────────────────

    def list_tables(self):
        """List all user tables in the public schema."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        return tables

    def create_table(self, table_name, columns):
        """
        Create a new table.
        columns: list of dicts with 'name' and 'type' keys.
        Example: [{"name": "id", "type": "SERIAL PRIMARY KEY"}, {"name": "embedding", "type": "vector(3)"}]
        """
        conn = self._get_connection()
        cur = conn.cursor()
        col_defs = ", ".join([f'"{c["name"]}" {c["type"]}' for c in columns])
        sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({col_defs});'
        cur.execute(sql)
        cur.close()
        LOG.info(f"Table '{table_name}' created.")
        return {"message": f"Table '{table_name}' created successfully."}

    def drop_table(self, table_name):
        """Drop a table."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')
        cur.close()
        LOG.info(f"Table '{table_name}' dropped.")
        return {"message": f"Table '{table_name}' dropped successfully."}

    def get_schema(self, table_name):
        """Get the column schema of a table."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        columns = []
        for row in cur.fetchall():
            columns.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2],
                "default": row[3]
            })
        cur.close()
        return columns

    # ─── Data Operations ──────────────────────────────────────

    def get_rows(self, table_name, limit=100, offset=0):
        """Get rows from a table with pagination."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(f'SELECT * FROM "{table_name}" LIMIT %s OFFSET %s;', (limit, offset))
        col_names = [desc[0] for desc in cur.description]
        rows = []
        for row in cur.fetchall():
            rows.append({col_names[i]: self._serialize(row[i]) for i in range(len(col_names))})
        cur.close()
        return {"columns": col_names, "rows": rows, "count": len(rows)}

    def insert_rows(self, table_name, rows):
        """
        Insert one or more rows into a table.
        rows: list of dicts, e.g. [{"name": "hello", "embedding": "[1,2,3]"}]
        """
        conn = self._get_connection()
        cur = conn.cursor()
        inserted = 0
        for row in rows:
            columns = ", ".join([f'"{k}"' for k in row.keys()])
            placeholders = ", ".join(["%s"] * len(row))
            values = list(row.values())
            sql = f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders});'
            cur.execute(sql, values)
            inserted += 1
        cur.close()
        return {"message": f"{inserted} row(s) inserted into '{table_name}'."}

    def update_rows(self, table_name, set_values, where_clause):
        """
        Update rows in a table.
        set_values: dict, e.g. {"name": "updated"}
        where_clause: string, e.g. "id = 1"
        """
        conn = self._get_connection()
        cur = conn.cursor()
        set_parts = ", ".join([f'"{k}" = %s' for k in set_values.keys()])
        values = list(set_values.values())
        sql = f'UPDATE "{table_name}" SET {set_parts} WHERE {where_clause};'
        cur.execute(sql, values)
        affected = cur.rowcount
        cur.close()
        return {"message": f"{affected} row(s) updated in '{table_name}'."}

    def delete_rows(self, table_name, where_clause):
        """
        Delete rows from a table.
        where_clause: string, e.g. "id = 1"
        """
        conn = self._get_connection()
        cur = conn.cursor()
        sql = f'DELETE FROM "{table_name}" WHERE {where_clause};'
        cur.execute(sql)
        affected = cur.rowcount
        cur.close()
        return {"message": f"{affected} row(s) deleted from '{table_name}'."}

    # ─── Query & Search ───────────────────────────────────────

    def execute_query(self, sql):
        """Execute a raw SQL query and return results."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(sql)

        if cur.description:
            col_names = [desc[0] for desc in cur.description]
            rows = []
            for row in cur.fetchall():
                rows.append({col_names[i]: self._serialize(row[i]) for i in range(len(col_names))})
            cur.close()
            return {"columns": col_names, "rows": rows, "count": len(rows)}
        else:
            affected = cur.rowcount
            cur.close()
            return {"message": f"Query executed successfully. {affected} row(s) affected."}

    def vector_search(self, table_name, column, query_vector, distance="cosine", limit=10):
        """
        Perform a vector similarity search.
        distance: 'cosine', 'l2', or 'inner_product'
        """
        distance_ops = {
            "cosine": "<=>",
            "l2": "<->",
            "inner_product": "<#>"
        }
        op = distance_ops.get(distance, "<=>")

        conn = self._get_connection()
        cur = conn.cursor()

        vector_str = str(query_vector) if isinstance(query_vector, list) else query_vector
        sql = f"""
            SELECT *, ("{column}" {op} %s::vector) AS distance
            FROM "{table_name}"
            ORDER BY "{column}" {op} %s::vector
            LIMIT %s;
        """
        cur.execute(sql, (vector_str, vector_str, limit))
        col_names = [desc[0] for desc in cur.description]
        rows = []
        for row in cur.fetchall():
            rows.append({col_names[i]: self._serialize(row[i]) for i in range(len(col_names))})
        cur.close()
        return {"columns": col_names, "rows": rows, "count": len(rows), "distance_metric": distance}

    # ─── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _serialize(value):
        """Serialize special Python types to JSON-safe values."""
        if value is None:
            return None
        if isinstance(value, (int, float, str, bool)):
            return value
        return str(value)
