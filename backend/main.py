import uvicorn
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from pathlib import Path
from pydantic import BaseModel

app = FastAPI()
redis_client = redis.Redis(host="localhost", port=6379)

FRONTEND = Path(__file__).parent.parent / "frontend"
WIDTH = 200
HEIGHT = 200
SOCKETS = set()

class Pixel(BaseModel):
    x: int
    y: int
    color: int

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

    for ws in list(SOCKETS):
        await ws.send_json({"x": pixel.x, "y": pixel.y, "color": pixel.color})

    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)