def get(name, query, config):

  import json
  import hapiserver

  if name == 'dataset':
    catalog, error = hapiserver.catalog({}, config)
    if error:
      return None, error

    try:
      datasets = json.loads(catalog)
    except Exception as e:
      error = {
        "code": 1500,
        "message_console": f"info(): Error parsing catalog JSON: {e}"
      }
      return None, error

    datasets = [dataset['id'] for dataset in datasets]
    if query['dataset'] not in datasets:
      error = {
        "code": 1407,
        "message_console": f"info(): dataset '{query['dataset']}' not found in catalog"
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

    info, error = hapiserver.info({'dataset': query['dataset']}, config)
    if error:
      return None, error

    parameters_known = []
    if parameters:
      parameters_known = [p['name'] for p in info.get('parameters', [])]

    for p in parameters.split(","):
      if p not in parameters_known:
        return None, {"code": 1407, "message_console": f"data(): Unknown parameter '{p}'"}

    return parameters, None