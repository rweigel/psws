__all__ = ["app", "get", "exec", "openapi", "error", "util", "run", "factory"]
__version__ = "0.0.1"

from hapiserver import openapi
from hapiserver import util
from hapiserver.app import app
from hapiserver.exec import exec
from hapiserver.error import error

import logging
logger = logging.getLogger(__name__)
# Allow logs to propagate to uvicorn's logger when run via
#   uvicorn hapiserver:factory ...
# on command line
logger.propagate = True

def run(config_file):
  import os
  import json
  import uvicorn
  import hapiserver

  if isinstance(config_file, str):
    with open(config_file, "r") as f:
      config_data = f.read()
      config = json.loads(config_data)

  if config['server']['workers'] == 1:
    app = hapiserver.app(config_file)
    uvicorn.run(app, **config['server'])
  else:
    # If multiple works, cannot start using uvicorn.run() because that
    # would start multiple instances of the main process.
    # The following approach does not work:
    #   uvicorn.run("hapiserver:factory", factory=True, **config['server'])

    os.environ["HAPI_CONFIG"] = config_file
    logger.info(f"Setting shell environment variable HAPI_CONFIG = {config_file}")
    args = ["uvicorn", "hapiserver:factory", "--factory"]
    if 'host' in config['server']:
      args += ["--host", str(config['server']['host'])]
    if 'port' in config['server']:
      args += ["--port", str(config['server']['port'])]
    if 'workers' in config['server']:
      args += ["--workers", str(config['server']['workers'])]
    logger.info(f"Executing shell command: {' '.join(args)}")
    os.execvp(args[0], args)


def factory(*args):
  """Factory function for uvicorn to create the app in each worker process.
  When
    HAPI_CONFIG=<file> uvicorn hapiserver:factory --factory ...
  is executed, this function is called to start each process.
  """
  import os
  import logging

  # Configure logging to work with uvicorn
  logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
  )

  # Ensure hapiserver logs are visible
  hapiserver_logger = logging.getLogger('hapiserver')
  hapiserver_logger.setLevel(logging.INFO)
  hapiserver_logger.propagate = True
  
  config = os.environ.get("HAPI_CONFIG")
  logger.info(f"Factory creating app with config: {config}")
  
  return app(config)