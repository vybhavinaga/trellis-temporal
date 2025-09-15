<!-- docs/TROUBLESHOOTING.md -->
# Troubleshooting

This file collects the main issues that came up while bringing the system together, and the changes that resolved them.

---

## Temporal Web not loading

Early runs showed the Web UI returning `14 UNAVAILABLE` or simply refusing to load.  
The issue was that the Temporal container was not yet healthy, and at times port 8080 was already in use locally.  
**Resolution:** stopped other services using 8080, restarted the stack from `infra/compose.yaml`, and waited until the container health checks passed. After that, the Web UI consistently loaded at `http://localhost:8080`.

---

## CLI confusion (`tctl` vs `temporal`)

Initially I used `tctl`, but it no longer matched the current Temporal deployment. The right approach was to install and use the new `temporal` CLI and always pass the explicit server address.  
**Resolution:** switched to `temporal --address localhost:7233 …` for all commands. This allowed listing workflows and confirming both open and closed executions without errors.

---

## Postgres schema mismatches

At one point, workflows failed with `UndefinedColumn` and `NotNullViolation` errors when writing to the `events` table. The root cause was that the schema in the container did not match what the activities expected.  
**Resolution:** reapplied the repo’s `schema.sql`, ensuring that `payments`, `events`, and `orders` were present with the correct columns. After this, idempotent upserts into `payments` and event appends worked as designed.

---

## Worker connection issues

The worker sometimes failed to connect to Postgres. The main cause was the `DATABASE_URL` not being exported correctly, or the Postgres container not ready yet.  
**Resolution:** fixed the environment to `postgresql://temporal:temporal@localhost:5432/temporal` and delayed worker startup until Postgres reported ready. Once corrected, the worker was able to poll both `orders-tq` and `shipping-tq` queues and execute workflows.

---

## Workflow timing and multiple errors

During testing, workflows would occasionally error out before completing, especially when manual review steps were involved. Some orders ended up timing out, even after signals were sent, because the **15s run timeout** cap on the parent workflow was being enforced strictly.  

At first, this produced confusing errors in the worker logs. After confirming the behavior, it was clear the workflows were still functioning correctly:  
- The manual review used `workflow.wait_condition`, which is deterministic, but if the timeout hit first, the workflow closed as `TimedOut`.  
- Cancel signals also led to similar behavior, where the order appeared as `TimedOut` rather than `Cancelled`.  

**Resolution:** no code changes were made — this was documented as the expected outcome. The important part was ensuring the worker polled both queues and that retries for the shipping child were in place. With those in place, workflows consistently reached a final state within the timeout window, even if not always `Completed`.

---

## Summary

Most issues were around environment setup and timing:  
- Ensuring the Temporal Web UI was accessible (container healthy, port 8080 free).  
- Using the correct CLI (`temporal`) with explicit address.  
- Keeping the Postgres schema aligned with the code.  
- Waiting for DB readiness before starting the worker.  
- Accepting that under a 15s cap, some workflows finish as `TimedOut` after cancel or manual review.  

Once these were resolved, the system ran reliably end to end.

---

## Future Improvements

A few areas stand out as next steps:

- **Explicit cancel handling**: Instead of allowing the workflow to close as `TimedOut`, add explicit cancel paths so users see `Cancelled` as the terminal state.  
- **CI/CD pipeline**: Automate build, test, and schema validation in CI to catch mismatches before local runs. Add GitHub Actions for worker + API tests.  
- **Resilience testing**: Simulate Postgres downtime and worker restarts to confirm idempotent activities behave as intended.  
- **Monitoring/alerts**: Integrate Temporal metrics and Postgres health checks with a dashboard (Prometheus/Grafana).  

These would make the system more production-ready while keeping the demo concise.
