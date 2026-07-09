"""Task status polling (SSE-friendly GET)."""
import asyncio

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.models.task import TaskStatus
from app.services import tasks

router = APIRouter(tags=["tasks"])


@router.get("/tasks")
def list_tasks():
    return tasks.list_recent_tasks()


@router.get("/tasks/{task_id}")
def get_task(task_id: int):
    return tasks.get_task(task_id)


@router.get("/tasks/{task_id}/events")
async def task_events(task_id: int):
    """Server-Sent Events: stream task progress until terminal."""
    async def event_gen():
        while True:
            t = tasks.get_task(task_id)
            if not t:
                yield {"event": "error", "data": "not found"}
                return
            yield {"data": {"status": t.status, "done": t.done, "total": t.total, "message": t.message}}
            if t.status in (TaskStatus.completed, TaskStatus.failed, TaskStatus.canceled):
                return
            await asyncio.sleep(1.0)
    return EventSourceResponse(event_gen())
