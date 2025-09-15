import asyncio
from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

@workflow.defn
class HelloWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return f"Hello, {name}!"

async def main():
    # Connect to your Temporal server running in Docker
    client = await Client.connect("localhost:7233")

    # Start a worker for workflows on task queue "hello-tq"
    worker = Worker(client, task_queue="hello-tq", workflows=[HelloWorkflow])
    async with worker:
        # Execute the workflow
        result = await client.execute_workflow(
            HelloWorkflow.run,
            "Vybhavi",
            id="hello-workflow",
            task_queue="hello-tq",
        )
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
