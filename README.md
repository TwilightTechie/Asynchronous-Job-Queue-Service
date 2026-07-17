# Asynchronous Job Queue Service

## Local development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload --port 8080
```

Then in another terminal:

```bash
curl localhost:8080/healthz
curl localhost:8080/readyz
```

## Tests

```bash
pytest
ruff check .
```

## Docker

```bash
docker build -t jobqueue .
docker run -d -p 8080:8080 --name jobqueue jobqueue
curl localhost:8080/healthz
docker rm -f jobqueue
```
