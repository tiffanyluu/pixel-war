import httpx
import time
import random
import os

TIME_TO_SLEEP = 50 #milliseconds
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:8000")
WIDTH = 200
HEIGHT = 200
NUM_COLORS = 16

client = httpx.Client()

while True:
    try:
        response = client.post(
            f"{SERVER_URL}/pixel",
            json={"x": random.randint(0, WIDTH-1), "y": random.randint(0, HEIGHT-1), "color": random.randint(0, NUM_COLORS-1)}
        )

        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"An error has occurred: {exc}")

    time.sleep(TIME_TO_SLEEP / 1000)

