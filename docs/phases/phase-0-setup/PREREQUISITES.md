# Phase 0 prerequisites (owner)

Everything here is free. Phase 0 makes no OpenAI calls.

| # | What | Why | How to check |
|---|---|---|---|
| 1 | A computer with at least 16 GB RAM and 30 GB free disk | Neo4j, Qdrant, Postgres and Redis run together | Windows: Task Manager > Performance |
| 2 | Windows 11 with **WSL2 + Ubuntu 24.04** (or macOS) | Docker and Python tools behave best on Linux | `wsl --status` in PowerShell |
| 3 | **Docker Desktop** with the WSL2 backend | Runs the database containers | `docker version` and `docker compose version` |
| 4 | **VS Code** with the extensions in `.vscode/extensions.json` (VS Code offers them when you open the folder) | Editor | Open the folder; accept "Install recommended extensions" |
| 5 | **Git** inside WSL | Clone the repository | `git --version` |
| 6 | **uv** (Python package manager) inside WSL | Installs Python 3.11 and the API packages | `uv --version` |
| 7 | **Node.js 22** inside WSL | Runs the web placeholder | `node --version` |
| 8 | GitHub: Claude GitHub App installed on the repository | Lets Claude push branches and open pull requests | Claude confirms |

Install commands inside the Ubuntu (WSL) terminal:

```bash
sudo apt update && sudo apt install -y git curl
curl -LsSf https://astral.sh/uv/install.sh | sh      # installs uv
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs
```

Docker Desktop is installed on Windows (not inside Ubuntu). In Docker Desktop >
Settings > Resources > WSL integration, turn on "Ubuntu".

Not needed yet: the OpenAI API key (Phase 1). When the time comes, you put it only in
the git-ignored `.env` file, never in chat or in Git.
