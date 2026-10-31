"""Servidor aislado con cierre cooperativo para las pruebas en Windows y Linux."""
import os
from pathlib import Path
import sys
import threading
import time

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
server = uvicorn.Server(uvicorn.Config("main:app", host="127.0.0.1", port=int(sys.argv[1]), log_level="warning"))
stop_file = Path(os.environ["ERP_TEST_STOP_FILE"])

def watch():
    while not stop_file.exists():
        time.sleep(.1)
    server.should_exit = True

threading.Thread(target=watch, daemon=True).start()
server.run()

