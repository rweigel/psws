__all__ = ["app", "get", "exec"]
__version__ = "0.0.1"

from hapiserver.app import app
from hapiserver.exec import exec

def serve():
  import os
  import json
  config = os.environ.get("HAPI_CONFIG")
  config = json.loads(config) if config else {}
  return app(config)