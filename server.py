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

def _cors_headers():
    return {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  }

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

  path = f"{patho}/catalog"


  logger.info(f"Initalizing endpoint {path}/")
  @app.route(path, methods=["GET", "HEAD"])
  def catalog(request: fastapi.Request):
    media_type = "application/json"

    #query_params = request.query_params
    # TODO: Verify no query parameters

    content, error = _cl_read(os.path.join(config.get("bin_dir"), "catalog.py"))

    if not error:
      return fastapi.responses.Response(content=content, media_type=media_type)
    else:
      content = {
        "status":{
          "code": error['hapi_code'],
          "message": f"Internal server error: {error['message']}"
        }
      }
      return fastapi.responses.Response(status_code=500, content=content, media_type=media_type)


  path = f"{patho}/info"
  logger.info(f"Initalizing endpoint {path}/")
  @app.route(path, methods=["GET", "HEAD"])
  def info(request: fastapi.Request):
    media_type = "application/json"

    query_params = request.query_params
    # TODO: Verify no query parameters

    if 'dataset' not in query_params:
      content = _get_error("1400")
      content['message'] = "Missing 'dataset' parameter"
      return fastapi.responses.Response(status_code=400, content=content)

    dataset = query_params['dataset']
    catalog, error = _cl_read(os.path.join(config.get("bin_dir"), "catalog.py"))
    if error:
      content = {
        "status":{
          "code": error['hapi_code'],
          "message": f"Internal server error: {error['message']}"
        }
      }
      return fastapi.responses.Response(status_code=500, content=content, media_type=media_type)

    if dataset not in catalog:
      content = _get_error("1406")
      return fastapi.responses.Response(status_code=406, content=content, media_type=media_type)

    info_script = os.path.join(config.get("bin_dir"), "info.py")
    content, error = _cl_read(info_script, dataset)
    if not error:
      return fastapi.responses.Response(content=content, media_type=media_type)
    else:
      content = {
        "status":{
          "code": error['hapi_code'],
          "message": f"Internal server error: {error['message']}"
        }
      }
      return fastapi.responses.Response(status_code=500, content=content, media_type=media_type)


  path = f"{patho}/data"
  logger.info(f"Initalizing endpoint {path}/")
  @app.route(path, methods=["GET", "HEAD"])
  def data(request: fastapi.Request):
    params = request.query_params

    if 'dataset' not in params:
      content = _get_error("1400")
      content['message'] = "Missing 'dataset' parameter"
      return fastapi.responses.Response(status_code=400, content=content) 
    if 'start' not in params:
      content = _get_error("1400")
      content['message'] = "Missing 'start' parameter"
      return fastapi.responses.Response(status_code=400, content=content) 
    if 'stop' not in params:
      content = _get_error("1400")
      content['message'] = "Missing 'stop' parameter"
      return fastapi.responses.Response(status_code=400, content=content) 

    dataset = params['dataset']
    catalog, error = _cl_read(os.path.join(config.get("bin_dir"), "catalog.py"))
    if error:
      content = {
        "status":{
          "code": error['hapi_code'],
          "message": f"Internal server error: {error['message']}"
        }
      }
      return fastapi.responses.Response(status_code=500, content=content, media_type="application/json")

    if dataset not in catalog:
      content = _get_error("1406")
      return fastapi.responses.Response(status_code=406, content=content)

    parameters = params.get('parameters', '')
    info_script = os.path.join(config.get("bin_dir"), "info.py")
    info, error = _cl_read(info_script, dataset)
    if error:
      content = {
        "status":{
          "code": error['hapi_code'],
          "message": f"Internal server error: {error['message']}"
        }
      }
      return fastapi.responses.Response(status_code=500, content=content, media_type="application/json")

    parameters_known = []
    if parameters:
      parameters_known = [p['name'] for p in info.get('parameters', [])]

    for p in parameters.split(","):
      if p not in parameters_known:
        content = _get_error("1407")
        return fastapi.responses.Response(status_code=400, content=content)

    # TODO: Convert start/stop to 20-character ISO format needed by data.py
    start = params['start']
    stop = params['stop']

    logger.info(f"Query params: {params}")
    script = os.path.join(config.get("bin_dir"), "data.py")
    args = f"{dataset} {start} {stop} {parameters}"

    stream_output, error = _cl_stream(script, args)
    if not error:
      media_type="text/csv"
      headers = _cors_headers()
      return fastapi.responses.StreamingResponse(stream_output(), media_type=media_type, headers=headers)
    else:
      content = {
        "status":{
          "code": error['code'],
          "message": f"Internal server error: {error['message']}"
        }
      }
      media_type = "application/json"
      return fastapi.responses.Response(status_code=500, content=content, media_type=media_type)


def _get_error(code):
  errors = {
    "1200": {"status":{"code": 1200, "message": "OK"}},
    "1201": {"status":{"code": 1201, "message": "OK - no data for time range"}},
    "1400": {"status":{"code": 1400, "message": "Bad request - user input error"}},
    "1401": {"status":{"code": 1401, "message": "Bad request - unknown API parameter name"}},
    "1402": {"status":{"code": 1402, "message": "Bad request - syntax error in start time"}},
    "1403": {"status":{"code": 1403, "message": "Bad request - syntax error in stop time"}},
    "1404": {"status":{"code": 1404, "message": "Bad request - start equal to or after stop"}},
    "1405": {"status":{"code": 1405, "message": "Bad request - start < startDate and/or stop > stopDate"}},
    "1406": {"status":{"code": 1406, "message": "Bad request - unknown dataset id"}},
    "1407": {"status":{"code": 1407, "message": "Bad request - unknown dataset parameter"}},
    "1408": {"status":{"code": 1408, "message": "Bad request - too much time or data requested"}},
    "1409": {"status":{"code": 1409, "message": "Bad request - unsupported output format"}},
    "1410": {"status":{"code": 1410, "message": "Bad request - unsupported include value"}},
    "1411": {"status":{"code": 1411, "message": "Bad request - out-of-order or duplicate parameters"}},
    "1412": {"status":{"code": 1412, "message": "Bad request - unsupported resolve_references value"}},
    "1413": {"status":{"code": 1413, "message": "Bad request - unsupported depth value"}},
    "1500": {"status":{"code": 1500, "message": "Internal server error"}},
    "1501": {"status":{"code": 1501, "message": "Internal server error - upstream request error"}}
  }

  return errors.get(code, errors["1500"])


def _cl_read(script, args=""):

  if not os.path.exists(script):
    content = "Execution script not found"
    logger.error(f"{content}: {script}")
    return None, {"hapi_code": 1500, "message": content}

  call = [sys.executable, script, *args.split()]
  logger.info(f"Executing: {' '.join(call)}")
  try:
    result = subprocess.run(
        call,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return result.stdout, None
  except Exception as e:
    message = f"Execution of script {script} failed"
    logger.error(f"{message}: {e}")
    return None, {"hapi_code": 1500, "message": message}


def _cl_stream(script, args=""):

  if not os.path.exists(script):
    content = f"Execution script {script} not found"
    logger.error(f"{content}: {script}")
    return None, {"hapi_code": 1500, "message": content}

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
    message = f"Execution of script {script} failed"
    logger.error(f"{message}: {e}")
    return None, {"hapi_code": 1500, "message": message}

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

  return stream_output, None


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
