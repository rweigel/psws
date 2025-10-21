# Not tested. Stub for HAPI server implementation

import os
import sys
import subprocess
import logging

import fastapi
import uvicorn

logger = logging.getLogger(__name__)
format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
logging.basicConfig(level='INFO', format=format)

def _api_init(app, config):

  patho = config.get("path", "/hapi").rstrip("/")

  logger.info(f"Initalizing endpoint {patho}/")
  @app.route(f"{patho}/", methods=["GET", "HEAD"])
  def indexhtml(request: fastapi.Request):
    # Silently ignores any query parameters
    fname = config.get("index_file")
    logger.info("Reading: " + fname)
    try:
      with open(fname) as f:
        response = f.read()
      return fastapi.responses.HTMLResponse(response)
    except Exception as e:
      logger.error(f"Error reading {fname}: {e}")
      return fastapi.responses.Response(status_code=500, content="Internal Server Error")

  path = f"{patho}/data"
  logger.info(f"Initalizing endpoint {path}/")
  @app.route(f"{path}/", methods=["GET", "HEAD"])
  def data(request: fastapi.Request):
    script = os.path.join(config.get("bin_dir"), "data.py")
    args = "W2NAF 2025-10-20T00:00:00Z 2025-10-22T00:00:00Z"
    return _cl_stream(script, args)


def _cl_stream(script, args="", media_type="text/plain"):

  if not os.path.exists(script):
    content = "Execution script not found"
    logger.error(f"{content}: {script}")
    return fastapi.responses.Response(status_code=500, content=content)

  call = [sys.executable, script, *args.split()]
  logger.info(f"Executing: {' '.join(call)}")
  try:
    proc = subprocess.Popen(
        call,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        text=True,
    )
  except Exception as e:
    content = "Execution of script failed"
    logger.error(f"{content}: {e}")
    return fastapi.responses.Response(status_code=500, content=content)

  def stream_output():
    try:
      # stream stdout lines as they arrive
      for line in proc.stdout:
        yield line
      proc.stdout.close()
      returncode = proc.wait()
      if returncode != 0:
        err = proc.stderr.read()
        logger.error(err)
        yield err
    finally:
      if proc.poll() is None:
        proc.kill()

  headers = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  }

  return fastapi.responses.StreamingResponse(stream_output(), media_type=media_type, headers=headers)


base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__)))

# Create the FastAPI app at module level so importing this module exposes `app`
app = fastapi.FastAPI()

base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__)))

api_config = {
  #"bin_dir": os.path.join(base_dir, "bin"),
  "bin_dir": base_dir,
  "index_file": os.path.join(base_dir, "index.html"),
  "path": "/hapi",
}

_api_init(app, api_config)

if __name__ == "__main__":
  run_config = {
                "host": "0.0.0.0",
                "port": 5555,
                "workers": 2,
                "server_header": False,
              }

  logger.info("Starting server")
  uvicorn.run("server:app", **run_config)
