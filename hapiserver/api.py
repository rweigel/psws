import json
import logging

import hapiserver

logger = logging.getLogger(__name__)

def api(config):

  return _fastapi(config)

def _fastapi(config):
  import fastapi

  app = fastapi.FastAPI()

  patho = config.get("path", "/hapi").rstrip("/")


  logger.info(f"Initalizing endpoint {patho}/")
  @app.route(f"{patho}/", methods=["GET", "HEAD"])
  def indexhtml(request: fastapi.Request):

    response = _indexhtml(config)
    return fastapi.responses.Response(**response)


  path = f"{patho}/catalog"
  logger.info(f"Initalizing endpoint {path}/")
  @app.route(path, methods=["GET", "HEAD"])
  def catalog(request: fastapi.Request):

    response = _catalog(request.query_params, config)
    return fastapi.responses.Response(**response)


  path = f"{patho}/info"
  logger.info(f"Initalizing endpoint {path}/")
  @app.route(path, methods=["GET", "HEAD"])
  def info(request: fastapi.Request):

    response = _info(request.query_params, config)
    return fastapi.responses.Response(**response)


  path = f"{patho}/data"
  logger.info(f"Initalizing endpoint {path}/")
  @app.route(path, methods=["GET", "HEAD"])
  def data(request: fastapi.Request):
    response = _data(request.query_params, config)

    if response.get('status_code', 200) != 200:
      return fastapi.responses.Response(**response)

    if isinstance(response['content'], str):
      return fastapi.responses.Response(**response)
    else:
      stream = response['content']
      del response['content']
      return fastapi.responses.StreamingResponse(stream(), **response)

  return app

def _query_params_dict(query_params):
  """Convert Starlette QueryParams to a plain dict.

  Args:
    query_params: Starlette QueryParams object

  Returns:
    dict: Plain dictionary with query parameter keys and values
  """

  if isinstance(query_params, dict):
    return query_params

  result = {}
  for key in query_params.keys():
    values = query_params.getlist(key)
    if len(values) == 1:
      result[key] = values[0]
    else:
      result[key] = values

  return result


def _query_param_error(endpoint, query):

  if endpoint == 'catalog':
    allowed = []
    required = []

  if endpoint == 'info':
    allowed = ["dataset"]
    required = ["dataset"]

  if endpoint == 'data':
    allowed = ["dataset", "start", "stop", "parameters"]
    required = ["dataset", "start", "stop"]

  for p in query:
    if p not in allowed and not p.startswith('x_'):
      return {
        "code": 1401,
        "message_console": f"info(): Unknown query parameter '{p}'"
      }

  for p in required:
    if p not in query:
      return {
        "code": 1400,
        "message": f"Missing '{p}' parameter"
      }

  return None


def _indexhtml(config):
  # Silently ignores any query parameters
  import os
  default = os.path.normpath(os.path.join(os.path.dirname(__file__)))
  default = os.path.join(default, "html", "index.html")
  fname = config.get("index.html", None)
  if fname is None:
    logger.info(f"No index.html configured, using default: {default}")
    fname = default

  logger.info("Reading: " + fname)
  try:
    with open(fname) as f:
      content = f.read()
      response = {
        "status_code": 200,
        "content": content,
      }
  except Exception as e:
    logger.error(f"Error reading {fname}: {e}")
    response = {
      "status_code": 404,
      "content": "Not Found",
    }

  response['media_type'] = "text/html"
  return response


def _catalog(query_params, config):
  import hapiserver

  logger.info(f"/catalog request: {query_params}")
  query = _query_params_dict(query_params)
  logger.info(f"/catalog request: {query}")

  error = _query_param_error('catalog', query)
  if error:
    return _error_response(error, config)

  if 'scripts' in config and 'catalog' in config['scripts']:
    catalog, error = hapiserver.exec(config["scripts"]["catalog"])
    if error:
      return _error_response(error, config)

  content = {
    "HAPI": config.get("HAPI", "3.0"),
    "status": {
      "code": 1200,
      "message": "OK"
    },
    "catalog": json.loads(catalog)
  }

  response = {
    "content": json.dumps(content, indent=2),
    "media_type": "application/json",
    "headers": _cors_headers(),
  }

  return response


def _info(query_params, config):
  import hapiserver

  logger.info(f"/info request: {query_params}")
  query = _query_params_dict(query_params)
  logger.info(f"/info request: {query}")

  error = _query_param_error('info', query)
  if error:
    return _error_response(error, config)

  dataset, error = _get('dataset', query, config)
  if error:
    return _error_response(error, config)

  if 'scripts' in config and 'info' in config['scripts']:
    info, error = hapiserver.exec(config["scripts"]["info"], dataset)
    if error:
      return _error_response(error, config)

  content = {
    "HAPI": config.get("HAPI", "3.0"),
    "status": {
      "code": 1200,
      "message": "OK"
    },
    **json.loads(info)
  }

  response = {
    "content": json.dumps(content, indent=2),
    "media_type": "application/json",
    "headers": _cors_headers(),
  }

  return response


def _data(query_params, config):

  logger.info(f"/data request: {query_params}")
  query = _query_params_dict(query_params)
  logger.info(f"/data request: {query}")

  error = _query_param_error('data', query)
  if error:
    return None, error

  for p in ['dataset', 'start', 'stop', 'parameters']:
    query[p], error = _get(p, query, config)
    if error:
      return _error_response(error, config)

  args = f"{query['dataset']} {query['start']} {query['stop']} {query['parameters']}"

  if 'scripts' in config and 'data' in config['scripts']:
    stream, error = hapiserver.exec(config["scripts"]["data"], args, stream=True)
    if error:
      return _error_response(error, config)

  response = {
    "content": stream,
    "media_type": "text/csv",
    "headers": _cors_headers()
  }

  return response


def _cors_headers():
    return {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  }


def _get(name, query, config):

  import json

  if name == 'dataset':
    response = _catalog({}, config)
    if response.get('status_code', 200) != 200:
      return response

    try:
      datasets = json.loads(response['content'])['catalog']
    except Exception as e:
      error = {
        "code": 1500,
        "message_console": f"_get(): Error parsing catalog JSON: {e}"
      }
      return None, error

    dataset_ids = [dataset['id'] for dataset in datasets]
    if query['dataset'] not in dataset_ids:
      error = {
        "code": 1407,
        "message_console": f"_get(): dataset '{query['dataset']}' not found in catalog"
      }
      return None, error

    return query['dataset'], None


  # TODO: Validate start/stop
  if name == 'start':
    return query['start'], None

  if name == 'stop':
    return query['stop'], None

  if name == 'parameters':

    if 'parameters' not in query:
      return '', None
    parameters = query['parameters']
    if parameters is None:
      return '', None
    if parameters == '':
      return '', None

    response = _info({'dataset': query['dataset']}, config)
    if response.get('status_code', 200) != 200:
      return response

    try:
      info = json.loads(response['content'])
    except Exception as e:
      error = {
        "code": 1500,
        "message_console": f"_get(): Error parsing info JSON: {e}"
      }
      return None, error


    parameters_known = []
    if parameters:
      parameters_known = [p['name'] for p in info.get('parameters', [])]

    for p in parameters.split(","):
      if p not in parameters_known:
        error = {
          "code": 1407,
          "message_console": f"data(): Unknown parameter '{p}'"
        }
        return None, error

    return parameters, None


def _error_response(error, config, message=None):

  if isinstance(error, int):
    error = _hapi_error(error, message=message)

  if 'message' not in error:
    message = _hapi_error(error['code'])['message']

  if 'exception' in error:
    if 'message_console' in error:
      logger.error(f"{error['message_console']}: {error['exception']}")
    else:
      logger.error(f"{message}: {error['exception']}")
  else:
    if 'message_console' in error:
      logger.error(f"{error['message_console']}")
    else:
      logger.error(f"{message}")

  content = {
    "status": {
      "code": error['code'],
      "message": message
    }
  }

  if error['code'] >= 1400 and error['code'] <= 1499:
    status_code = 400
  if error['code'] >= 1500 and error['code'] <= 1599:
    status_code = 500
  if error['code'] == 1500:
    status_code = 500
  if error['code'] == 1501:
    status_code = 501

  response = {
    "status_code": status_code,
    "content": json.dumps(content, indent=2),
    "media_type": "application/json",
  }

  return response


def _hapi_error(code, message=None):
  errors = {
    1200: {"status":{"code": 1200, "message": "OK"}},
    1201: {"status":{"code": 1201, "message": "OK - no data for time range"}},
    1400: {"status":{"code": 1400, "message": "Bad request - user input error"}},
    1401: {"status":{"code": 1401, "message": "Bad request - unknown API parameter name"}},
    1402: {"status":{"code": 1402, "message": "Bad request - syntax error in start time"}},
    1403: {"status":{"code": 1403, "message": "Bad request - syntax error in stop time"}},
    1404: {"status":{"code": 1404, "message": "Bad request - start equal to or after stop"}},
    1405: {"status":{"code": 1405, "message": "Bad request - start < startDate and/or stop > stopDate"}},
    1406: {"status":{"code": 1406, "message": "Bad request - unknown dataset id"}},
    1407: {"status":{"code": 1407, "message": "Bad request - unknown dataset parameter"}},
    1408: {"status":{"code": 1408, "message": "Bad request - too much time or data requested"}},
    1409: {"status":{"code": 1409, "message": "Bad request - unsupported output format"}},
    1410: {"status":{"code": 1410, "message": "Bad request - unsupported include value"}},
    1411: {"status":{"code": 1411, "message": "Bad request - out-of-order or duplicate parameters"}},
    1412: {"status":{"code": 1412, "message": "Bad request - unsupported resolve_references value"}},
    1413: {"status":{"code": 1413, "message": "Bad request - unsupported depth value"}},
    1500: {"status":{"code": 1500, "message": "Internal server error"}},
    1501: {"status":{"code": 1501, "message": "Internal server error - upstream request error"}}
  }

  if message is not None:
    # Augment the standard message with the provided one
    errors[code]['status']['message'] += f". {message}"

  return errors.get(code, errors[1500])['status']
