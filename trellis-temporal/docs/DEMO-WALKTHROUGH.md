<!-- docs/DEMO-WALKTHROUGH.md -->
# Demo Walkthrough

This walkthrough shows the system running end-to-end with screenshots from Temporal Web, API output, and DB verification.

---

When the infrastructure is up, Temporal Web lists both the **OrderWorkflow** (parent) and **ShippingWorkflow** (child). The worker is polling both `orders-tq` and `shipping-tq`, so as soon as an order is placed both workflows are present.

![infra up](img/06-infra-up.png)  
![worker polling](img/07-worker-polling.png)  
![workflows list](img/01-workflows-list.png)

---

The order summary shows signals being processed — address update, approve, and eventually a successful completion. In the history you can see the **StartChildWorkflowExecutionInitiated** event, which triggers the child shipping workflow.

![order summary](img/02-order-summary.png)  
![order history with child](img/03-order-history-child-event.png)  
![shipping summary with parent link](img/04-shipping-summary-parent-link.png)

---

During a normal “happy path,” the API logs and Temporal Web confirm the order is approved, the charge recorded, and the shipping dispatched. The events table in Postgres contains the audit trail of workflow events.

![API happy path](img/05-api-happy-path.png)  
![events table](img/08-events-table.png)

---

In the cancel variant, the workflow moves into a **TimedOut** state after cancellation. This is the current intended behavior: cancel signals are honored, but the short run timeout (15s) means the order times out soon after.

![cancel flow](img/09-cancel-flow.png)

---

Retries were configured for the shipping child: if dispatch fails, the parent retries once. In this demo run it succeeded on the first attempt, but the workflow definition ensures retry is covered.
