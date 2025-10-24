# Usage:
#   python serve_test.py [<config_file>]

import time
import logging
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def log_test_title(url):
  line = len(url)*"-"
  logger.info(line)
  logger.info(f"Testing {url}")
  logger.info(line)


def wait_for_server(url, retries=50, delay=0.2):
  # Wait for the server to start
  print(f"Checking if server is ready by making request to {url} ...")
  for i in range(retries):
    try:
      response = requests.get(url, timeout=0.5)
      if response.status_code == 200:
        break
    except Exception:
      print(f"Server not ready. Next try in {delay} sec...")
      time.sleep(delay)
  else:
    raise RuntimeError(f"Server did not start after {retries} attempts.")


def start_server(config_file):
  import json
  import atexit
  import multiprocessing

  with open(config_file, "r") as f:
    config = json.load(f)

  logger.info("Starting server in background process")
  kwargs = {
    "target": start_server_process,
    "args": (config,),
    "daemon": True
  }
  server_proc = multiprocessing.Process(**kwargs)
  server_proc.start()
  atexit.register(stop_server, server_proc)


def start_server_process(config):
  import uvicorn
  import hapiserver
  app = hapiserver.app(config['api'])
  logger.info("Starting server")
  uvicorn.run(app, **config['server'])


def stop_server(server_proc):
  try:
    if server_proc.is_alive():
      logger.info("Terminating server process")
      server_proc.terminate()
      server_proc.join(timeout=2)
  except Exception:
    pass


def run_tests(port, config_file):

  start_server(config_file)

  url_base = f"http://0.0.0.0:{port}/hapi"

  wait_for_server(url_base, retries=4, delay=0.5)

  url = url_base
  log_test_title(url)
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/html' in response.headers['Content-Type']
  assert 'HAPI' in response.text

  url = f"{url_base}/catalog"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'application/json' in response.headers['Content-Type']
  assert 'catalog' in response.json()
  assert len(response.json()['catalog']) > 0

  url = f"{url_base}/info?dataset=S000028"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'application/json' in response.headers['Content-Type']
  assert 'parameters' in response.json()
  assert len(response.json()['parameters']) > 0

  url = f"{url_base}/data?dataset=S000028&&start=2025-10-20T00:00:00Z&stop=2025-10-20T00:00:01Z"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/csv' in response.headers['Content-Type']
  assert response.text.startswith('2025-10-20T00:00:00Z')

  url = f"{url_base}/data?dataset=S000028&&start=2025-10-20T00:00:00Z&stop=2025-10-20T00:00:01Z&parameters=Field_Vector"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/csv' in response.headers['Content-Type']
  assert response.text.startswith('2025-10-20T00:00:00Z')

if __name__ == "__main__":
  import sys
  if len(sys.argv) > 1:
    config_file = sys.argv[1]
  else:
    config_file = "/Users/weigel/git/hapi/server-python-general/bin/psws/config.json"
  run_tests(5999, config_file)
