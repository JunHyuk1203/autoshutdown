import asyncio
import websockets
import json
import threading
import time

async def handler(ws):
    print('Client connected!')
    try:
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        print('Received:', msg)
        await ws.send(json.dumps({'type': 'auth_result', 'status': 'success'}))
        print('Auth sent!')
        async for m in ws:
            print('MSG:', m)
    except Exception as e:
        print('Handler error:', e)

async def serve():
    async with websockets.serve(handler, '0.0.0.0', 9999):
        print('Server started on port 9999')
        await asyncio.Future()

asyncio.run(serve())
