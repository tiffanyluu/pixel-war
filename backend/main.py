import json
import os
import uvicorn
import redis.asyncio as redis
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from pathlib import Path
from pydantic import BaseModel
from contextlib import asynccontextmanager

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.Redis.from_url(REDIS_URL)

FRONTEND = Path(__file__).parent.parent / "frontend"
WIDTH = 200
HEIGHT = 200
SOCKETS = set()

class Pixel(BaseModel):
    x: int
    y: int
    color: int


async def background_work():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("pixels")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
            except Exception as e:
                print(f"Unexpected error: {e}")
                continue
            for ws in list(SOCKETS):
                try:
                    await ws.send_json(data)
                except Exception:
                    SOCKETS.discard(ws)
    finally:
        await pubsub.unsubscribe()
                


@asynccontextmanager
async def lifespan(app:FastAPI):
    worker_task = asyncio.create_task(background_work())
    yield
    print("server is shutting down")
    worker_task.cancel()

    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    print("All lifespan background tasks fully drained.")


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=FileResponse)
async def index():
    return FRONTEND / "index.html"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    SOCKETS.add(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        SOCKETS.discard(websocket)
        print("websocket closed")


@app.get("/canvas")
async def get_canvas():
    raw_bytes = await redis_client.get("canvas") or b""
    return Response(content=raw_bytes, media_type="application/octet-stream")


@app.post("/pixel")
async def set_pixel(pixel: Pixel):
    if not (0 <= pixel.x < WIDTH and 0 <= pixel.y < HEIGHT and 0 <= pixel.color <= 15):
        raise HTTPException(status_code=400, detail="pixel out of range")
    
    index = pixel.y * WIDTH + pixel.x
    await redis_client.bitfield("canvas").set("u4", f"#{index}", pixel.color).execute()

    await redis_client.publish("pixels", json.dumps({"x": pixel.x, "y": pixel.y, "color": pixel.color}))

    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)