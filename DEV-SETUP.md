# Development setup

Copy `.env.example` to `.env`, then set a database password and secret key locally.

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Open http://localhost:4200. The frontend proxies requests to the backend; frontend
and backend source changes reload automatically. Plain `docker compose up` uses
the production build. Enable the optional upload drop-box with `--profile webdav`.

For native development, install Python dependencies with `uv sync` and frontend
dependencies with `pnpm install` in `src-ui`. Run backend tests with `uv run pytest`
and frontend tests with `pnpm test`. Run checks with `uv run prek run --all-files`.

Deployment-specific hosts, credentials, paths and Compose overrides belong in
ignored local files. This repository does not automatically deploy to a server.
