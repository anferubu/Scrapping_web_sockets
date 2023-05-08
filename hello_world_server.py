import asyncio
import websockets


async def hello(websocket, path):
    name = await websocket.recv()
    print(f'Received {name}')

    greeting = f'Hello, {name}'

    await websocket.send(greeting)
    print(f'Sent {greeting}')


async def main():
    async with websockets.serve(hello, 'localhost', 8765):
        await asyncio.Future()


asyncio.run(main())