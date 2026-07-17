# Asynchronous Job Queue Service

## Local development

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload --port 8080

Then in another terminal:

curl localhost:8080/healthz
curl localhost:8080/readyz

## Tests

pytest
ruff check .

## Docker

docker build -t jobqueue .
docker run -d -p 8080:8080 --name jobqueue jobqueue
curl localhost:8080/healthz
docker rm -f jobqueue
