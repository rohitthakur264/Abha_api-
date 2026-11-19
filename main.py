"""FastAPI entrypoint wiring production ABDM routes and optional demo routes."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

import config
import routes_abdm
import routes_demo
from store import log
from webhook_reader import poll_loop, seed_existing_webhook_items


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=== ABDM M2 Link Token Demo starting ===")
    log.info("Demo polling enabled=%s | Demo routes enabled=%s", config.ENABLE_WEBHOOK_POLLING, config.ENABLE_DEMO_ROUTES)
    task = None
    if config.ENABLE_WEBHOOK_POLLING:
        await seed_existing_webhook_items()
        task = asyncio.create_task(poll_loop())
    yield
    if task:
        task.cancel()


app = FastAPI(title="ProDoc ABDM Middleware (M1 ABHA & M2 Care Context)", lifespan=lifespan)
app.include_router(routes_abdm.router)
if config.ENABLE_DEMO_ROUTES:
    app.include_router(routes_demo.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

