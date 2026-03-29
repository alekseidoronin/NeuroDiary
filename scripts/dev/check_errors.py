
import asyncio
from app.db.engine import async_session
from app.db.models import ProviderJob
from sqlalchemy import select, desc

async def check_errors():
    async with async_session() as session:
        res = await session.execute(
            select(ProviderJob)
            .where(ProviderJob.kind == "llm")
            .order_by(desc(ProviderJob.started_at))
            .limit(10)
        )
        jobs = res.scalars().all()
        for job in jobs:
            print(f"Time: {job.started_at} | Status: {job.status} | Model: {job.model} | Error: {job.error_message}")

if __name__ == '__main__':
    asyncio.run(check_errors())
