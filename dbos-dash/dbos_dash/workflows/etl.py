import random
import time

from dbos import DBOS, Queue

fast_queue = Queue("fast-queue", concurrency=3)


@DBOS.step()
def fetch_data(source: str) -> dict:
    DBOS.logger.info(f"Fetching data from {source}...")
    time.sleep(0.2)
    return {"source": source, "rows": random.randint(10, 500)}


@DBOS.step()
def transform(data: dict) -> dict:
    DBOS.logger.info(f"Transforming {data['rows']} rows from {data['source']}")
    time.sleep(0.1)
    return {**data, "transformed": True, "output_rows": data["rows"] * 2}


@DBOS.step()
def load_result(data: dict) -> str:
    DBOS.logger.info(f"Loading {data['output_rows']} rows")
    time.sleep(0.1)
    return f"Loaded {data['output_rows']} rows from {data['source']}"


@DBOS.workflow()
def etl_pipeline(source: str) -> str:
    raw = fetch_data(source)
    transformed = transform(raw)
    result = load_result(transformed)
    from .greeting import send_notification

    send_notification(result)
    return result


@DBOS.workflow()
def parallel_pipeline(sources: list) -> dict:
    handles = []
    for source in sources:
        h = fast_queue.enqueue(etl_pipeline, source)
        handles.append(h)

    results = []
    for h in handles:
        results.append(h.get_result())

    from .greeting import send_notification

    summary = f"Processed {len(results)} sources"
    send_notification(summary)
    return {"summary": summary, "results": results}
