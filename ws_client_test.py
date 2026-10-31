import argparse
import asyncio
import getpass
import json
import os
import websockets

async def listen(uri, token):
    async with websockets.connect(uri) as websocket:
        await websocket.send(token)
        async for message in websocket:
            print(json.dumps(json.loads(message), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cliente autenticado de eventos ERP')
    parser.add_argument('--url', default='ws://127.0.0.1:8000/ws/updates')
    args = parser.parse_args()
    token = os.getenv('ERP_TOKEN') or getpass.getpass('Token de acceso: ')
    try:
        asyncio.run(listen(args.url, token))
    except KeyboardInterrupt:
        pass

