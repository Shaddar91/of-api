FROM python:3.13-slim AS build
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore --prefix=/install -r requirements.txt

FROM python:3.13-slim
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
COPY --from=build /install /usr/local
WORKDIR /srv
COPY app/ app/
USER 10001
EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:create_app()"]
