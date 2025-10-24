import os
import logging

import uvicorn

import hapiserver

logger = logging.getLogger(__name__)
format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
logging.basicConfig(level='INFO', format=format)


import sys
import json
if len(sys.argv) > 1:
  config_file = sys.argv[1]
else:
  config_file = "/Users/weigel/git/hapi/server-python-general/bin/psws/config.json"
with open(config_file, "r") as f:
  config = json.load(f)

def catalog():
  return [{"id": "S000028"}, {"id": "S000082"}]

if False:
  del config['api']['scripts']['catalog']
  config['api']['functions'] = {"catalog": catalog}

if __name__ == "__main__" and config.get("server", {}).get("workers", 1) > 1:
  import sys
  import json
  os.environ["HAPI_CONFIG"] = json.dumps(config['api'])
  uvicorn.run("hapiserver:serve", factory=True, **config["server"])
  sys.exit(0)
else:
  app = hapiserver.app(config['api'])
  logger.info("Starting server")
  uvicorn.run(app, **config['server'])
