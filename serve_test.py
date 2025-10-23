# Usage:
#   python serve_test.py

import time
import logging
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def _log_test_title(url):
  line = len(url)*"-"
  logger.info(line)
  logger.info(f"Testing {url}")
  logger.info(line)


def _wait_for_server(url, retries=50, delay=0.2):
  # Wait for the server to start
  print("Checking if server is ready by making request to /config ...")
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


def _run_tests(port, config):

  base = f"http://0.0.0.0:{port}/hapi"
  url = base

  _wait_for_server(url, retries=4, delay=0.5)

  _log_test_title(url)
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/html' in response.headers['Content-Type']
  assert 'HAPI' in response.text

  url = f"{base}/catalog"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'application/json' in response.headers['Content-Type']
  assert 'catalog' in response.json()
  assert len(response.json()['catalog']) > 0

  url = f"{base}/info?dataset=S000028"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'application/json' in response.headers['Content-Type']
  assert 'parameters' in response.json()
  assert len(response.json()['parameters']) > 0

  url = f"{base}/data?dataset=S000028&&start=2025-10-20T00:00:00Z&stop=2025-10-20T00:00:01Z"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/csv' in response.headers['Content-Type']
  assert response.text.startswith('2025-10-20T00:00:00Z')

  url = f"{base}/data?dataset=S000028&&start=2025-10-20T00:00:00Z&stop=2025-10-20T00:00:01Z&parameters=Field_Vector"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/csv' in response.headers['Content-Type']
  assert response.text.startswith('2025-10-20T00:00:00Z')

if __name__ == "__main__":
  _run_tests(5999, {})
