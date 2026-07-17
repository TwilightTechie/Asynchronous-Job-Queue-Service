# syntax=docker/dockerfile:1

FROM python:3.12-slim AS build

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime

RUN useradd --create-home --shell /usr/sbin/nologin appuser
WORKDIR /app

COPY --from=build /install /usr/local
COPY app/ ./app/

USER appuser

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
