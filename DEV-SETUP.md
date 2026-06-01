# Development Setup

## Quick start

```bash
docker compose up -d
```

This automatically applies `docker-compose.override.yml`, which adds:

| Service | URL | Notes |
|---|---|---|
| Angular dev server (HMR) | http://localhost:4200 | Frontend with live reload |
| Django / granian (API + WS) | http://localhost:8000 | Backend in debug mode |

The first start takes a few extra minutes while pnpm installs frontend dependencies into an isolated Docker volume (`frontend_nm`).

## Live reload behaviour

**Frontend** — Angular HMR is on by default. Any change to `src-ui/` is reflected in the browser within seconds.

**Backend** — `src/` is mounted into the container and granian runs with `--reload` (via `GRANIAN_RELOAD=true`). Python changes trigger an automatic server restart. For changes that require a migration, run:

```bash
docker compose exec webserver python manage.py migrate
```

## Resetting the frontend node_modules volume

If you hit strange pnpm/node errors after a lockfile update:

```bash
docker volume rm paperless_frontend_nm
docker compose up -d
```

## Running production mode locally

Pass only the base file to skip the override:

```bash
docker compose -f docker-compose.yml up -d
```
