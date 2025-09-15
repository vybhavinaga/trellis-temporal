# Trellis Temporal

> **Temporal (Python SDK) + FastAPI + Postgres demo:**  
Implements Order → Shipping (parent/child) workflows with signals, query, idempotent charge, and event logging.

---

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quickstart](#quickstart)
  - [1. Clone & Install](#1-clone--install)
  - [2. Infra: Temporal + Web + Postgres](#2-infra-temporal--web--postgres)
  - [3. Run Worker & API (two terminals)](#3-run-worker--api-two-terminals)
  - [4. Happy Path Example](#4-happy-path-example)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Workflow Criteria](#workflow-criteria)
- [References](#references)
- [Demo-Walkthrough](#demo-Walkthrough && troubleshooting documentation)

---

## Features

- **Parent/Child Workflow:** Order triggers Shipping workflow.
- **Signals:** Approve, cancel, update_address.
- **Query:** status.
- **Idempotent charge:** Payments upsert (ON CONFLICT DO NOTHING).
- **Event Logging:** All workflow events persisted.
- **Retry logic:** Shipping retried once on dispatch_failed.
- **Manual review:** Via workflow.wait_condition (deterministic).
- **Timeout:** Parent run capped at 15s.

---

## Prerequisites

- **Docker Desktop**
- **Python 3.11** (local venv at `.venv`)
- `curl` and (optional) [`jq`](https://stedolan.github.io/jq/) for pretty JSON  
  - macOS: `brew install jq`
  - Windows: `winget install jqlang.jq` (optional)

> **Database URL used:**  
> `DATABASE_URL=postgresql://temporal:temporal@localhost:5432/temporal`

---

## Quickstart

### 1. Clone & Install

#### macOS/Linux (bash)
```bash
git clone https://github.com/vybhavinaga/trellis-temporal.git
cd trellis-temporal
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
#### Windows (PowerShell)
```powershell
git clone https://github.com/vybhavinaga/trellis-temporal.git
cd trellis-temporal
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

---

### 2. Infra: Temporal + Web + Postgres

#### macOS/Linux (bash)
```bash
cd infra
./up.sh
cd -
```
#### Windows (PowerShell)
```powershell
docker compose -f infra/compose.yaml up -d --build
```

#### Verify containers & schema
```bash
docker compose -f infra/compose.yaml ps
docker exec -it temporal-postgresql psql -U temporal -d temporal -c '\dt'
# expect: payments, events, orders
```
- **Temporal Web:** [http://localhost:8080](http://localhost:8080)
- **Temporal gRPC:** `localhost:7233`

Check Postgres container name:
```bash
docker ps --format '{{.Names}}' | grep -x temporal-postgresql
```

---

### 3. Run Worker & API (two terminals)

#### macOS/Linux (bash)
```bash
# terminal 1
source .venv/bin/activate
.venv/bin/python worker.py    # polls orders-tq + shipping-tq

# terminal 2
source .venv/bin/activate
.venv/bin/python api.py       # FastAPI on http://127.0.0.1:8000
```
#### Windows (PowerShell)
```powershell
# terminal 1
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python worker.py    # polls orders-tq + shipping-tq

# terminal 2
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python api.py       # FastAPI on http://127.0.0.1:8000
```
---

### 4. Happy Path Example

#### macOS/Linux (bash)
```bash
curl -s -X POST http://127.0.0.1:8000/orders/123/start | jq
curl -s -X POST http://127.0.0.1:8000/orders/123/signals/update_address \
  -H 'Content-Type: application/json' -d '{"address":"42 Galaxy Way"}' | jq
curl -s -X POST http://127.0.0.1:8000/orders/123/signals/approve | jq
curl -s http://127.0.0.1:8000/orders/123/status | jq
```
#### Windows (PowerShell)
```powershell
curl -s -X POST http://127.0.0.1:8000/orders/123/start | jq
curl -s -X POST http://127.0.0.1:8000/orders/123/signals/update_address `
  -H 'Content-Type: application/json' `
  -d '{"address":"42 Galaxy Way"}' | jq
curl -s -X POST http://127.0.0.1:8000/orders/123/signals/approve | jq
curl -s http://127.0.0.1:8000/orders/123/status | jq
```

> Temporal Web should show `OrderWorkflow` (parent) and `ShippingWorkflow` (child).

---

## Testing

#### macOS/Linux (bash)
```bash
# ensure infra is up (section 2)
PYTHONPATH=. .venv/bin/python -m pytest -q
```
#### Windows (PowerShell)
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python -m pytest -q
```
#### Run subsets:
```bash
# API smoke only
PYTHONPATH=. .venv/bin/pytest -q tests/test_api_smoke.py
# activities only
PYTHONPATH=. .venv/bin/pytest -q -k activities
# (PowerShell: replace the python path with .\.venv\Scripts\python -m pytest ...)
```

---

## Troubleshooting

- **Temporal Web 8080 not loading:**  
  `docker compose -f infra/compose.yaml ps` — check for port clash.
- **Child not running:**  
  Confirm worker logs show polling `orders-tq` and `shipping-tq`.
- **DB connect errors:**  
  Verify `DATABASE_URL` matches above; pg_isready:  
  `docker exec -it temporal-postgresql pg_isready -U temporal -d temporal`
- **Temporal CLI (optional):**  
  `temporal --address localhost:7233 workflow list --open`

---

## Workflow Criteria

- **Signals:** approve, cancel, update_address
- **Query:** status
- **Child:** ShippingWorkflow (run_id[:6] used for child ID)
- **Retry:** parent retries shipping once on dispatch_failed
- **Idempotent charge:** payments upsert (ON CONFLICT DO NOTHING)
- **Events persisted:** events(type, payload_json)
- **Manual review:** via workflow.wait_condition (deterministic)
- **Parent run timeout cap:** 15s

---

## References

- [Temporal Python SDK](https://docs.temporal.io/dev-guide/python/introduction)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Postgres Documentation](https://www.postgresql.org/docs/)
- [jq](https://stedolan.github.io/jq/)

## Demo-Walkthrough && Troubleshooting documentation

See [`DEMO-WALKTHROUGH`](trellis-temporal/docs/DEMO-WALKTHROUGH.md) for a full visual walkthrough, including Temporal Web UI, API outputs, and typical workflow runs and [`TROUBLESHOOTING`](trellis-temporal/docs/TROUBLESHOOTING.md) here I’ve documented the main issues I encountered while setting up and running the project, along with the changes that resolved them.
