import time

from dbos import DBOS


@DBOS.step()
def send_notification(message: str) -> str:
    DBOS.logger.info(f"Notification: {message}")
    time.sleep(0.05)
    return f"Notified: {message}"


@DBOS.workflow()
def greet_workflow(name: str) -> str:
    return send_notification(f"Hello, {name}!")
