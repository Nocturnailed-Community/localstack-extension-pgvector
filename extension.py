import logging
import os
from localstack.extensions.api import Extension, http
from localstack.utils.container_utils import container_client

LOG = logging.getLogger(__name__)

class PgVectorExtension(Extension):
    name = "pgvector"

    def on_platform_ready(self):
        LOG.info("PgVector extension is ready!")

    def on_container_start(self, container_info):
        """
        Hook called when a new container starts.
        We check if it's a PostgreSQL container and inject our init script.
        """
        # Note: LocalStack uses various naming conventions for containers.
        # We look for containers that likely run PostgreSQL.
        container_name = container_info.get("Config", {}).get("Image", "")
        if "postgres" in container_name.lower():
            LOG.info(f"Detected PostgreSQL container: {container_info.get('Id')}. Injecting pgvector init script.")
            
            # Path to our init.sql
            init_sql_path = os.path.join(os.path.dirname(__file__), "init.sql")
            
            if os.path.exists(init_sql_path):
                try:
                    # Target path in the container
                    target_path = "/docker-entrypoint-initdb.d/01_pgvector.sql"
                    
                    container_id = container_info.get("Id")
                    with open(init_sql_path, "rb") as f:
                        container_client.copy_into_container(container_id, f.read(), target_path)
                    
                    LOG.info(f"Successfully injected {init_sql_path} into {container_id}:{target_path}")
                    
                    # [NEW] Launch pgweb sidecar
                    self._launch_pgweb(container_info)
                    
                except Exception as e:
                    LOG.error(f"Failed to inject pgvector init script: {e}")
            else:
                LOG.warning(f"init.sql not found at {init_sql_path}")

    def _launch_pgweb(self, postgres_container_info):
        """
        Launches a pgweb container connected to the detected postgres instance.
        """
        pgweb_container_name = "localstack-pgweb-pgvector"
        
        # Check if already running
        existing = container_client.get_container_status(pgweb_container_name)
        if existing:
            LOG.info("pgweb container is already running.")
            return

        try:
            LOG.info("Starting pgweb sidecar...")
            
            # Get postgres container network info
            # We want to connect via the container name/IP in the same network
            postgres_ip = postgres_container_info.get("NetworkSettings", {}).get("IPAddress")
            # Fallback to localstack host if needed, but container-to-container is better
            db_url = f"postgres://postgres:postgres@{postgres_ip}:5432/postgres?sslmode=disable"
            
            # Note: In a real LocalStack environment, we might need to handle credentials/DB name dynamically
            # For now, we use defaults.
            
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

    @http.route("/pgvector-status", methods=["GET"])
    def check_status(self, request):
        """
        Health check endpoint to verify the extension is loaded.
        """
        return {
            "status": "enabled",
            "extension": "pgvector",
            "pgweb_url": "http://localhost:8081",
            "message": "LocalStack pgvector extension + pgweb are active."
        }
