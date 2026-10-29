FROM python:3.12-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY /backend ./backend/

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/backend

CMD ["python", "bot.py"]