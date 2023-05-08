import asyncio
import websockets


async def hello():
    async with websockets.connect("ws://localhost:8765") as websocket:
        name = input("What is your name? ")

        await websocket.send(name)
        print(f"Sent {name}")

        greeting = await websocket.recv()
        print(f"Received {greeting}")


asyncio.run(hello())