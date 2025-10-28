import json
import logging

import hapiserver

logger = logging.getLogger(__name__)

def app(config):
  import fastapi

  if isinstance(config, str):
    with open(config, "r") as f:
      config = f.read()
      config = json.loads(config)
    config = config.get('api', {})

  hapiserver.util.set_env(config)
  hapiserver.util.expand_env(config)
  hapiserver.util.check_config(config)

  # TODO: It seems that much of the following could be auto-generated based
  # on the OpenAPI spec. fastapi-code-generator seems to apply partially,
  # but also may require quite a bit of manual configuration.

  # Create FastAPI app with custom OpenAPI configuration
  logger.info("Initalizing endpoints /docs, /redoc, and /openapi.json")
  app_kwargs = hapiserver.openapi.kwargs(['info'])
  app_kwargs['version'] = config.get("HAPI", "3.3")
  app = fastapi.FastAPI(**app_kwargs)


  patho = config.get("path", "/hapi").rstrip("/")

  path = f"{patho}/"
  logger.info(f"Initalizing endpoint {path}")
  root_kwargs = hapiserver.openapi.kwargs(['paths', path, 'get'])
  @app.head(path)
  @app.get(path, response_class=fastapi.responses.HTMLResponse, **root_kwargs)
  def indexhtml(request: fastapi.Request):
    response = _indexhtml(config)
    return fastapi.responses.Response(**response)


  path = f"{patho}/catalog"
  logger.info(f"Initalizing endpoint {path}/")
  catalog_kwargs = hapiserver.openapi.kwargs(['paths', path, 'get'])
  @app.head(path)
  @app.get(path, response_class=fastapi.responses.JSONResponse, **catalog_kwargs)
  def catalog(request: fastapi.Request):
    response = _catalog(request.query_params, config)
    return fastapi.responses.Response(**response)


  path = f"{patho}/info"
  logger.info(f"Initalizing endpoint {path}/")
  info_kwargs = hapiserver.openapi.kwargs(['paths', path, 'get'])
  @app.head(path)
  @app.get(path, response_class=fastapi.responses.JSONResponse, **info_kwargs)
  def info(request: fastapi.Request):
    response = _info(request.query_params, config)
    return fastapi.responses.Response(**response)


  path = f"{patho}/data"
  logger.info(f"Initalizing endpoint {path}/")
  data_kwargs = hapiserver.openapi.kwargs(['paths', path, 'get'])
  @app.head(path)
  @app.get(path, **data_kwargs)
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

  response['headers'] = _headers(config['HAPI'], cors=False)
  response['media_type'] = "text/html"
  return response


def _call(endpoint, query_params, config):
  import hapiserver

  logger.info(f"/{endpoint} request: {query_params}")
  query = _query_params_dict(query_params)
  logger.info(f"/{endpoint} request: {query}")

  error = _query_param_error(endpoint, query)
  if error:
    return None, error

  args = {}
  if endpoint == 'info':
    dataset, error = _get('dataset', query, config)
    args = {"dataset": dataset}
    if error:
      return None, error

  if 'scripts' in config and endpoint in config['scripts']:
    args = [str(args[x]) for x in args.keys()]
    args = " ".join(args)
    if len(args) > 0:
      data, error = hapiserver.exec(config["scripts"][endpoint], args=args)
    else:
      data, error = hapiserver.exec(config["scripts"][endpoint])
    if error:
      return None, error

    try:
      data = json.loads(data)
    except Exception as e:
      error = {
        "code": 1500,
        "message": "Error parsing JSON returned by catalog script",
        "exception": e
      }
      return None, error

    return data, None

  if 'functions' in config and endpoint in config['functions']:
    try:
      args = [str(args[x]) for x in args.keys()]
      if len(args) > 0:
        data = config['functions'][endpoint](*args)
      else:
        data = config['functions'][endpoint]()
    except Exception as e:
      error = {
        "code": 1500,
        "message": f"Error executing {endpoint} function",
        "exception": e
      }
      return None, error

    return data, None


def _catalog(query_params, config):

  catalog, error = _call('catalog', query_params, config)
  if error:
    return hapiserver.error(error, config)

  content = {
    "HAPI": config.get("HAPI", "3.0"),
    "status": {
      "code": 1200,
      "message": "OK"
    },
    "catalog": catalog
  }

  response = {
    "content": json.dumps(content, indent=2),
    "media_type": "application/json",
    "headers": _headers(config['HAPI']),
  }

  return response


def _info(query_params, config):
  import hapiserver

  logger.info(f"/info request: {query_params}")
  query = _query_params_dict(query_params)
  logger.info(f"/info request: {query}")

  error = _query_param_error('info', query)
  if error:
    return hapiserver.error(error, config)

  dataset, error = _get('dataset', query, config)
  if error:
    return hapiserver.error(error, config)

  if 'scripts' in config and 'info' in config['scripts']:
    info, error = hapiserver.exec(config["scripts"]["info"], dataset)
    if error:
      return hapiserver.error(error, config)

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
    "headers": _headers(config['HAPI']),
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
      return hapiserver.error(error, config)

  args = f"{query['dataset']} {query['start']} {query['stop']} {query['parameters']}"

  if 'scripts' in config and 'data' in config['scripts']:
    stream, error = hapiserver.exec(config["scripts"]["data"], args, stream=True)
    if error:
      return hapiserver.error(error, config)

  response = {
    "content": stream,
    "media_type": "text/csv",
    "headers": _headers(config['HAPI']),
  }

  return response


def _headers(hapi_version, cors=True):
  server = f"HAPI/{hapi_version} Server"
  server += ";https://github.com/hapi-server/server-python-general"
  server += f"; v{hapiserver.__version__}"
  headers = {"Server": server}
  if cors:
    headers.update({
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    })
  return headers


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


