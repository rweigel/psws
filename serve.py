import os
import logging

import uvicorn

import hapiserver

logger = logging.getLogger(__name__)
format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
logging.basicConfig(level='INFO', format=format)

base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__)))

config = {
  "api": {
    "index.html": os.path.join(base_dir, "html", "index.html"),
    "path": "/hapi",
    "HAPI": "3.3",
    "scripts": {
      "catalog": os.path.join(base_dir, "bin", "psws", "catalog.py"),
      "info": os.path.join(base_dir, "bin", "psws", "info.py"),
      "data": os.path.join(base_dir, "bin", "psws", "data.py")
    }
  },
  "ENV": {
    "DATA_DIR": os.path.join(base_dir, "data", "psws")
  },
  "server": {
    "host": "0.0.0.0",
    "port": 5999,
    "workers": 1,
    "server_header": False,
  }
}

for name, value in config.get("ENV", {}).items():
  os.environ[name] = str(value)
  logger.info(f"Environment variable set: {name}={value}")

app = hapiserver.api(config['api'])
logger.info("Starting server")
uvicorn.run(app, **config['server'])
