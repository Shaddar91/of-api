# of-api

Flask API for the of-web login page, served by Gunicorn. It checks a username and password against Postgres, returns an opaque bearer token, and stores only the token's SHA-256 with its expiry. The image runs Python 3.13 as uid 10001 on port 8000.

## API

| Request | Response |
|---|---|
| `POST /api/v1/login` with `{"username","password"}` | 200 `{"token","expires_at","username"}` |
| `POST /api/v1/login` without both fields as non-empty strings | 400 `{"error":"username and password required"}` |
| `POST /api/v1/login` with a wrong username or password | 401 `{"error":"invalid credentials"}` |
| `GET /api/v1/me` with `Authorization: Bearer <token>` | 200 `{"username","expires_at"}` |
| `POST /api/v1/logout` with the bearer | 204, and the token's row is deleted |
| `me` or `logout` with a missing, unknown or expired token | 401 `{"error":"invalid token"}` |

`expires_at` is RFC 3339 in UTC, `TOKEN_TTL_SECONDS` after the login. `GET /healthz` returns `{"status":"ok"}` without querying Postgres, so it stays 200 while the database is down. `GET /api/v1/hello` returns `{"message":"hello"}`.

## Configuration

| Variable | Default | Secret | Use |
|---|---|---|---|
| `DATABASE_URL` | unset | yes | Postgres URL; when set, the `DB_*` variables are ignored |
| `DB_HOST`, `DB_PORT`, `DB_NAME` | `localhost`, `5432`, `of` | no | parts of the URL the app builds when `DATABASE_URL` is unset |
| `DB_USER`, `DB_PASSWORD` | `of`, empty | yes | the same; both are percent-encoded into the URL |
| `TOKEN_TTL_SECONDS` | `3600` | no | token lifetime |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | no | comma-separated browser origins allowed to call the API |
| `OF_API_USER_PASSWORD` | unset | yes | password that `flask --app app create-user NAME` sets for NAME, replacing an existing one |

In the cluster the Helm chart leaves `DATABASE_URL` unset, sets the non-secret variables, takes `DB_USER` and `DB_PASSWORD` from a Kubernetes Secret, and runs `flask --app app init-db` in an init container before the API starts.

## Run it with Compose

```sh
docker compose up --build
```

This starts Postgres 17 and the API on `127.0.0.1:8000`. Before Gunicorn starts, the API container runs `flask --app app init-db`, which creates `users` and `tokens` if they are missing, and `flask --app app create-user demo`. The passwords for `demo` and for Postgres are dev-only values kept in `compose.yaml`. Set `OF_API_PORT` or `OF_DB_PORT` to move the host ports off 8000 or 5432. From a second terminal, log in and read the row the login wrote:

```sh
curl -s localhost:8000/api/v1/login -H 'content-type: application/json' \
  -d '{"username":"demo","password":"<OF_API_USER_PASSWORD from compose.yaml>"}'
docker compose exec db psql -U of -c 'select user_id, token_hash, expires_at from tokens'
```

`docker compose down -v` removes the containers and the database volume; plain `down` keeps users and tokens for the next start. Without Docker, on Python 3.13 with `DATABASE_URL` set: `pip install -r requirements.txt`, the same two `flask` commands, then `gunicorn -b 0.0.0.0:8000 'app:create_app()'`.

## The whole stack

`../dev-lane/compose.yaml`, in a folder beside the of-api and of-web checkouts and outside both repos, includes this repo's `compose.yaml` and adds the of-web dev server. Its README has the start and stop commands. With it up:

- `http://localhost:5173`: the of-web login page; sign in as `demo` with the password from `compose.yaml`
- `http://localhost:8000`: this API, which the page calls
- `localhost:5432`: Postgres, user and database `of`

## Tests

The fixtures truncate `users` and `tokens` before each test, so the suite needs a throwaway Postgres; pointed at the Compose database it deletes `demo`. This runs ruff and pytest in the image's Python against a database that exists only for the run:

```sh
docker run -d --name of-api-test-db -e POSTGRES_USER=of -e POSTGRES_DB=of \
  -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17-alpine
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp --network container:of-api-test-db \
  -e DATABASE_URL=postgresql://of@localhost:5432/of -v "$PWD":/srv -w /srv python:3.13-slim \
  sh -c 'python -m venv /tmp/v && . /tmp/v/bin/activate && pip install -q -r requirements-dev.txt && ruff check . && pytest -q'
docker rm -f of-api-test-db
```

Without `DATABASE_URL`, only `tests/test_app.py` and the CORS tests pass; the others error with "DATABASE_URL must name a disposable Postgres".

## Two architectures, one ECR repository

A published commit has three tags in one ECR repository: `<sha>-amd64`, `<sha>-arm64`, and `<sha>`, an image index that lists the other two. The chart's `image.tag` is `<sha>` on both node types; a node pulling it reads the index and downloads only the image built for its own CPU, so Graviton nodes run arm64 and x86 nodes run amd64. The of-helm values file picks the node. `values-graviton.yaml` selects `kubernetes.io/arch: arm64` and tolerates the `arch=arm64:NoSchedule` taint that Karpenter's `graviton` NodePool puts on its nodes, and `values-x86.yaml` selects `amd64`, which the `x86` NodePool supplies. A per-arch tag works as a pin only next to its matching values file; on a node of the other architecture it fails with `exec format error`.

## CI

`.github/workflows/ci.yml` runs ruff and pytest against a `postgres:17-alpine` service container on every push and pull request to `master`, then builds the image natively on an amd64 and an arm64 runner and checks `/healthz` in each. When the repository variable `DEPLOY_ENABLED` is `true`, a push to `master` publishes `<sha>-amd64`, `<sha>-arm64` and the `<sha>` index, skipping tags that already exist because the repository is immutable. The file is generated, so an edit made to it here is overwritten.
