<p align="center">
  <img src="https://raw.githubusercontent.com/Nocturnailed-Community/localstack-extension-pgvector/main/pgvector.png" alt="pgvector-extension Logo" width="200">
</p>

# LocalStack pgvector Extension 🚀

[![Install LocalStack Extension](https://localstack.cloud/gh/extension-badge.svg)](https://app.localstack.cloud/extensions/remote?url=git+https://github.com/Nocturnailed-Community/localstack-extension-pgvector/#egg=localstack-extension-pgvector)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**localstack-extension-pgvector** is a professional extension for LocalStack designed to simplify the development of AI-driven applications and Vector Search. This extension automatically enables `pgvector` on every PostgreSQL instance running in LocalStack and provides a web interface via `pgweb`.

---

## ✨ Key Features

- **Auto-Enable pgvector:** Automatically executes `CREATE EXTENSION IF NOT EXISTS vector;` when a PostgreSQL container starts.
- **pgweb Integration:** Automatically launches a `pgweb` (Web UI) instance as a sidecar to visualize your vector data.
- **Seamless Integration:** Supports standard RDS and PostgreSQL instances in LocalStack.
- **Health Check Endpoint:** Verify extension status via a dedicated HTTP endpoint.

---

## 🛠️ Installation

### Using LocalStack Dashboard (Recommended)
Click the badge above or open the [LocalStack Extensions Dashboard](https://app.localstack.cloud/extensions) and enter this repository URL:
`https://github.com/Nocturnailed-Community/localstack-extension-pgvector`

### Using CLI
Use the following command to install the extension locally:
```bash
localstack extensions install "https://github.com/Nocturnailed-Community/localstack-extension-pgvector"
```

### Local Development (Editable Mode)
1. Clone this repository.
2. Run:
   ```bash
   pip install -e .
   ```
3. Restart LocalStack.

### 🐳 Using Docker Compose

For easy local development, you can use the provided `docker-compose.yml`:

1.  Start LocalStack:
    ```bash
    docker compose up -d
    ```
2.  The extension will be installed automatically. Check status:
    ```bash
    curl http://localhost:4566/pgvector-status
    ```

---

## 🛠️ Usage

1. **Start LocalStack:**
   ```bash
   localstack start
   ```
2. **Launch PostgreSQL/RDS:**
   Use AWS CLI or SDK to create a database instance. Example:
   ```bash
   awslocal rds create-db-instance --db-instance-identifier mydb --engine postgres --allocated-storage 20
   ```
3. **Access pgweb:**
   Open your browser and navigate to `http://localhost:8081` to view your data.
4. **Check Status:**
   Verify if the extension is active:
   `http://localhost:4566/pgvector-status`

---

## 📡 API Reference (v0.2.0)

All endpoints are accessible via `http://localhost:4566/pgvector/...`

### Status
```bash
curl http://localhost:4566/pgvector/status
```

### Table Management

**List tables:**
```bash
curl http://localhost:4566/pgvector/tables
```

**Create a table (with vector column):**
```bash
curl -X POST http://localhost:4566/pgvector/tables \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "documents",
    "columns": [
      {"name": "id", "type": "SERIAL PRIMARY KEY"},
      {"name": "content", "type": "TEXT"},
      {"name": "embedding", "type": "vector(3)"}
    ]
  }'
```

**Get table schema:**
```bash
curl http://localhost:4566/pgvector/tables/documents/schema
```

**Drop a table:**
```bash
curl -X DELETE http://localhost:4566/pgvector/tables/documents
```

### Data Operations

**Insert rows:**
```bash
curl -X POST http://localhost:4566/pgvector/tables/documents/data \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [
      {"content": "Hello AI", "embedding": "[1,2,3]"},
      {"content": "Vector DB", "embedding": "[4,5,6]"}
    ]
  }'
```

**Get rows (with pagination):**
```bash
curl "http://localhost:4566/pgvector/tables/documents/data?limit=10&offset=0"
```

**Update rows:**
```bash
curl -X PUT http://localhost:4566/pgvector/tables/documents/data \
  -H "Content-Type: application/json" \
  -d '{"set": {"content": "Updated"}, "where": "id = 1"}'
```

**Delete rows:**
```bash
curl -X DELETE http://localhost:4566/pgvector/tables/documents/data \
  -H "Content-Type: application/json" \
  -d '{"where": "id = 1"}'
```

### Raw SQL Query
```bash
curl -X POST http://localhost:4566/pgvector/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM pg_extension WHERE extname = '\''vector'\'';"}'
```

### 🔍 Vector Similarity Search
```bash
curl -X POST http://localhost:4566/pgvector/search \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "documents",
    "column": "embedding",
    "query_vector": [1, 2, 3],
    "distance": "cosine",
    "limit": 5
  }'
```

**Supported distance metrics:** `cosine`, `l2`, `inner_product`

---

## 👨‍💻 Contributors

- **Muhammad Ikhwan Fathulloh** ([@Muhammad-Ikhwan-Fathulloh](https://github.com/Muhammad-Ikhwan-Fathulloh))
- Email: `muhammadikhwanfathulloh17@gmail.com`

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ by <b>Noc Lab</b> as part of the LocalStack ecosystem.
</p>
