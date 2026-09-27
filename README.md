# of-api
Smallest stateless Flask API: `GET /healthz` returns `{"status":"ok"}` and `GET /api/v1/hello` returns `{"message":"hello"}`. The image runs Python 3.13 as uid 10001 on port 8000.
Run: `pip install -r requirements.txt && gunicorn -b 0.0.0.0:8000 'app:create_app()'`, or `docker build -t of-api . && docker run -p 8000:8000 of-api`.
Test: `pip install -r requirements-dev.txt && ruff check . && pytest -q`.
CI (`.github/workflows/ci.yml`) runs ruff and pytest, then builds and smoke-tests the image natively on amd64 and arm64 runners, for every push and PR to `master`. Once the repo variable `DEPLOY_ENABLED` is `true`, `master` runs assume the `AWS_ROLE_ARN` secret over OIDC in `AWS_REGION`, push `ECR_REPOSITORY:<sha>-<arch>` for each arch, then join both into the multi-arch `ECR_REPOSITORY:<sha>`.
