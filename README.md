<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/paperflow-ai-logo-dark.svg">
    <img alt="Paperflow AI" src="docs/assets/paperflow-ai-logo-light.svg" width="440">
  </picture>
</p>

# Paperflow AI

Paperflow AI is a fork of [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) that focuses on **AI-assisted document management** while keeping the core "scan, archive, search" workflow that paperless-ngx is known for.

This repository intentionally trims down some of the upstream project’s scope:

- ✅ Keep: core document management, search, tags, web UI
- ✅ Add: AI-powered features (chat over your documents, smarter extraction, Mistral integration)
- ✅ Keep: modern tooling (Python 3.14, `uv`, Docker support)
- ❌ Drop: complex multi-target release packaging and container publishing logic from upstream CI
- ❌ Drop: upstream-specific badges, demo links, and community references

Paperflow AI is **not** a drop-in replacement for paperless-ngx, but a focused fork optimized for experimentation with AI features on top of a solid DMS foundation.

---

## Key differences vs paperless-ngx

Compared to upstream paperless-ngx, Paperflow AI:

- Ships an **agentic dashboard chat** that searches across _all_ your documents
  with tool-driven retrieval and dynamic citations. It is built on upstream's
  llama-index AI stack (`src/paperless_ai/agent_chat.py`) and reuses the same
  streaming protocol as the built-in per-document chat.
- Supports Mistral chat/embeddings through the OpenAI-compatible backend, and
  includes a Mistral OCR parser with Markdown/image output. Remote OCR can run
  automatically or selectively through upstream's workflow controls.
- Uses **`uv` as the Python dependency manager** for local development and CI.
- Simplifies the **CI pipeline** to focus on tests and static checks instead of multi-target releases and Docker image publishing.

The goal is to make it easy to:

- Run a personal document archive at home.
- Experiment with new AI-powered extraction, search and chat flows.
- Keep the project maintainable as a smaller fork.

---

## Getting started

The recommended way to run Paperflow AI is via Docker Compose, similar to upstream paperless-ngx.

### Quick start with Docker Compose

Copy `.env.example` to `.env` and configure secrets locally first. For an existing
installation, set `COMPOSE_PROJECT_NAME` to the existing project name before
starting, to preserve the association with its database/media volumes.

From this repository on your server:

```bash
cd paperflow-ai
docker compose build
docker compose up -d
```

`docker compose` uses [docker-compose.yml](docker-compose.yml) by default, which is the **production** deployment (built image, no source mounts, bound to localhost port 8000 by default). The provided `docker-compose.yml` expects environment variables for API keys and secrets (e.g. Mistral, database password). Check the `webserver` service section and configure the relevant variables (preferably via a `.env` file) before running in production.

To run the **development** stack instead (Angular dev server with HMR on `http://localhost:4200`, live source mounts, Django auto-reload), opt in with the dev override:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

AI is disabled by default. Configure your provider locally before enabling it:

| Variable                             | Purpose                                                      |
| ------------------------------------ | ------------------------------------------------------------ |
| `PAPERLESS_AI_ENABLED`               | Master switch for the AI suite (chat + index).               |
| `PAPERLESS_AI_LLM_API_KEY`           | API key for the embedding/chat backend (your Mistral key).   |
| `PAPERLESS_AI_LLM_EMBEDDING_BACKEND` | Embedding backend: `openai-like`, `huggingface` or `ollama`. |
| `PAPERLESS_AI_LLM_EMBEDDING_MODEL`   | Embedding model name (e.g. `mistral-embed`).                 |
| `PAPERLESS_AI_LLM_BACKEND`           | Chat LLM backend: `openai-like` or `ollama`.                 |
| `PAPERLESS_AI_LLM_MODEL`             | Chat model name (e.g. `mistral-large-latest`).               |
| `PAPERLESS_MISTRAL_API_KEY`          | Enables the Mistral OCR parser; unset → Tesseract.           |
| `PAPERLESS_MISTRAL_MODEL`            | Mistral OCR model (default `mistral-ocr-latest`).            |

> Note: This fork assumes you are comfortable managing your own Docker deployment. There is no one-line install script or hosted demo like the upstream project.

---

## Upgrading this fork to v3.2

Back up the database, media and data volumes before upgrading. Keep local
credentials, hosts and volume/project names in `.env` or an ignored Compose
override. Set `COMPOSE_PROJECT_NAME` to the existing project name; changing it
makes Compose select different named volumes.

This merge retains the fork's Django migration history and reconciles it with
upstream. The AI index now uses upstream sqlite-vec instead of LanceDB. Rebuild
it from existing document content after migration:

```sh
docker compose exec webserver python manage.py document_llmindex rebuild
```

Indexing can make billable embedding calls. Document files do not need to be
re-OCRed. Keep the old database/data backups for rollback; rolling back only the
container image does not reverse database/index migrations.

## Development setup (with `uv`)

Paperflow AI uses [`uv`](https://github.com/astral-sh/uv) for Python dependency management and tooling.

### Prerequisites

- Python 3.14 (the only supported Python minor version, matching the production image)
- `uv` installed (`pip install uv` or via your package manager)

### Install dependencies

```bash
cd paperflow-ai
uv sync --dev
```

This will create and manage a virtual environment and install all development dependencies defined in `pyproject.toml`.

### Common tasks

Run tests:

```bash
uv run pytest
```

Run the development server (Django):

```bash
cd src
uv run manage.py runserver
```

Lint and format using pre-commit hooks (also used in CI):

```bash
uv run prek run --all-files
```

---

## CI pipeline (fork-specific)

The fork retains checks for backend/frontend tests, linting, static analysis and
container builds. Upstream publishing, release, translation and maintenance
workflows remain removed. There is no deployment automation tied to a personal
server. Keep credentials and deployment overrides in ignored local files.

---

## Security note

As with upstream paperless-ngx:

> Document scanners are typically used to scan sensitive documents like your social insurance number, tax records, invoices, etc. **Paperflow AI should never be run on an untrusted host** because information is stored in clear text without encryption. No guarantees are made regarding security (but we do try!) and you use the app at your own risk.
>
> **The safest way to run Paperflow AI is on a local server in your own home with backups in place.**

---

## License

Paperflow AI is licensed under the same license as paperless-ngx. See [LICENSE](LICENSE) for details.
