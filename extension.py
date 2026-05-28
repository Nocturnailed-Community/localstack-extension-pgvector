import json
import logging
import os
from localstack.extensions.api import Extension
from localstack.extensions.api.http import RouteHandler, Router, Response, Request
from localstack.utils.container_utils import container_client

from db_manager import DatabaseManager

LOG = logging.getLogger(__name__)


class PgVectorExtension(Extension):
    name = "pgvector"

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()

    # ─── Lifecycle Hooks ──────────────────────────────────────

    def on_extension_load(self):
        LOG.info("pgvector extension loaded.")

    def on_platform_ready(self):
        LOG.info("pgvector extension is ready! Database management API is active.")

    def on_platform_shutdown(self):
        LOG.info("pgvector extension shutting down. Closing DB connections.")
        self.db.close()

    # ─── Route Registration ───────────────────────────────────

    def update_gateway_routes(self, router: Router[RouteHandler]):
        LOG.info("Registering pgvector management routes...")

        # Status
        router.add("/pgvector/status", self.handle_status)

        # Table management
        router.add("/pgvector/tables", self.handle_tables, methods=["GET", "POST"])
        router.add("/pgvector/tables/<table_name>", self.handle_table_detail, methods=["DELETE"])
        router.add("/pgvector/tables/<table_name>/schema", self.handle_table_schema, methods=["GET"])

        # Data management
        router.add("/pgvector/tables/<table_name>/data", self.handle_table_data, methods=["GET", "POST", "PUT", "DELETE"])

        # Query & Search
        router.add("/pgvector/query", self.handle_query, methods=["POST"])
        router.add("/pgvector/search", self.handle_search, methods=["POST"])

        LOG.info("All pgvector routes registered.")

    # ─── Container Hooks ──────────────────────────────────────

    def on_container_start(self, container_info):
        container_name = container_info.get("Config", {}).get("Image", "")
        if "postgres" in container_name.lower():
            LOG.info(f"Detected PostgreSQL container: {container_info.get('Id')}. Injecting pgvector init script.")

            init_sql_path = os.path.join(os.path.dirname(__file__), "init.sql")

            if os.path.exists(init_sql_path):
                try:
                    target_path = "/docker-entrypoint-initdb.d/01_pgvector.sql"
                    container_id = container_info.get("Id")
                    with open(init_sql_path, "rb") as f:
                        container_client.copy_into_container(container_id, f.read(), target_path)
                    LOG.info(f"Successfully injected init.sql into {container_id}:{target_path}")

                    # Update DB manager connection using container network
                    postgres_ip = container_info.get("NetworkSettings", {}).get("IPAddress", "localhost")
                    self.db.host = postgres_ip
                    LOG.info(f"Database manager connected to {postgres_ip}")

                    self._launch_pgweb(container_info)
                except Exception as e:
                    LOG.error(f"Failed to inject pgvector init script: {e}")
            else:
                LOG.warning(f"init.sql not found at {init_sql_path}")

    def _launch_pgweb(self, postgres_container_info):
        pgweb_container_name = "localstack-pgweb-pgvector"

        existing = container_client.get_container_status(pgweb_container_name)
        if existing:
            LOG.info("pgweb container is already running.")
            return

        try:
            LOG.info("Starting pgweb sidecar...")
            postgres_ip = postgres_container_info.get("NetworkSettings", {}).get("IPAddress")
            db_url = f"postgres://postgres:postgres@{postgres_ip}:5432/postgres?sslmode=disable"

            container_client.run_container(
                image="sosedoff/pgweb",
                name=pgweb_container_name,
                detach=True,
                ports={8081: 8081},
                env={"DATABASE_URL": db_url},
                command=["--bind=0.0.0.0", "--listen=8081"]
            )
            LOG.info(f"pgweb started at http://localhost:8081 (connected to {postgres_ip})")
        except Exception as e:
            LOG.error(f"Failed to launch pgweb: {e}")

    # ─── Helpers ──────────────────────────────────────────────

    def _json_response(self, data, status=200):
        return Response(
            response=json.dumps(data, default=str),
            status=status,
            mimetype="application/json"
        )

    def _get_json_body(self, request):
        try:
            return json.loads(request.data)
        except Exception:
            return {}

    # ─── Route Handlers ───────────────────────────────────────

    def handle_status(self, request: Request, **kwargs):
        return self._json_response({
            "status": "enabled",
            "extension": "pgvector",
            "version": "0.2.0",
            "pgweb_url": "http://localhost:8081",
            "endpoints": [
                "GET  /pgvector/status",
                "GET  /pgvector/tables",
                "POST /pgvector/tables",
                "DELETE /pgvector/tables/<name>",
                "GET  /pgvector/tables/<name>/schema",
                "GET  /pgvector/tables/<name>/data",
                "POST /pgvector/tables/<name>/data",
                "PUT  /pgvector/tables/<name>/data",
                "DELETE /pgvector/tables/<name>/data",
                "POST /pgvector/query",
                "POST /pgvector/search",
            ]
        })

    def handle_tables(self, request: Request, **kwargs):
        try:
            if request.method == "GET":
                tables = self.db.list_tables()
                return self._json_response({"tables": tables})

            elif request.method == "POST":
                body = self._get_json_body(request)
                table_name = body.get("table_name")
                columns = body.get("columns", [])
                if not table_name or not columns:
                    return self._json_response({"error": "Missing 'table_name' or 'columns'."}, 400)
                result = self.db.create_table(table_name, columns)
                return self._json_response(result, 201)
        except Exception as e:
            return self._json_response({"error": str(e)}, 500)

    def handle_table_detail(self, request: Request, table_name: str, **kwargs):
        try:
            result = self.db.drop_table(table_name)
            return self._json_response(result)
        except Exception as e:
            return self._json_response({"error": str(e)}, 500)

    def handle_table_schema(self, request: Request, table_name: str, **kwargs):
        try:
            schema = self.db.get_schema(table_name)
            return self._json_response({"table": table_name, "columns": schema})
        except Exception as e:
            return self._json_response({"error": str(e)}, 500)

    def handle_table_data(self, request: Request, table_name: str, **kwargs):
        try:
            if request.method == "GET":
                limit = int(request.args.get("limit", 100))
                offset = int(request.args.get("offset", 0))
                result = self.db.get_rows(table_name, limit, offset)
                return self._json_response(result)

            elif request.method == "POST":
                body = self._get_json_body(request)
                rows = body.get("rows", [])
                if not rows:
                    return self._json_response({"error": "Missing 'rows' array."}, 400)
                result = self.db.insert_rows(table_name, rows)
                return self._json_response(result, 201)

            elif request.method == "PUT":
                body = self._get_json_body(request)
                set_values = body.get("set", {})
                where = body.get("where", "")
                if not set_values or not where:
                    return self._json_response({"error": "Missing 'set' or 'where'."}, 400)
                result = self.db.update_rows(table_name, set_values, where)
                return self._json_response(result)

            elif request.method == "DELETE":
                body = self._get_json_body(request)
                where = body.get("where", "")
                if not where:
                    return self._json_response({"error": "Missing 'where' clause."}, 400)
                result = self.db.delete_rows(table_name, where)
                return self._json_response(result)
        except Exception as e:
            return self._json_response({"error": str(e)}, 500)

    def handle_query(self, request: Request, **kwargs):
        try:
            body = self._get_json_body(request)
            sql = body.get("sql", "")
            if not sql:
                return self._json_response({"error": "Missing 'sql' field."}, 400)
            result = self.db.execute_query(sql)
            return self._json_response(result)
        except Exception as e:
            return self._json_response({"error": str(e)}, 500)

    def handle_search(self, request: Request, **kwargs):
        try:
            body = self._get_json_body(request)
            table_name = body.get("table_name")
            column = body.get("column")
            query_vector = body.get("query_vector")
            distance = body.get("distance", "cosine")
            limit = body.get("limit", 10)

            if not all([table_name, column, query_vector]):
                return self._json_response({"error": "Missing 'table_name', 'column', or 'query_vector'."}, 400)

            result = self.db.vector_search(table_name, column, query_vector, distance, limit)
            return self._json_response(result)
        except Exception as e:
            return self._json_response({"error": str(e)}, 500)
