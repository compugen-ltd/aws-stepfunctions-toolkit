FROM ghcr.io/astral-sh/uv:0.9.18 AS uv
FROM python:3.13

WORKDIR /app

RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen

COPY --chmod=777 src/ .

ENTRYPOINT [ "./.venv/bin/python", "./main.py" ]