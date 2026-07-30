from celery import Celery
from app.config import settings

celery_app = Celery(
    "hsbot",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task
def process_file_task(file_path: str, filename: str):
    from app.services.rag import RAGService
    from app.database import async_session
    import asyncio

    async def _process():
        async with async_session() as session:
            svc = RAGService(session)
            return await svc.process_file(file_path, filename)

    return asyncio.run(_process())
