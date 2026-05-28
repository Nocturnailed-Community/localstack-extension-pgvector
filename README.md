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

---

## 🚀 Usage

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

## 📊 Manual Verification

You can run the following query to ensure `pgvector` is enabled:
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

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
