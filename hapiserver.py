import os
import sys

import hapiserver
import argparse
parser = argparse.ArgumentParser(description="HAPI server")
parser.add_argument("config", nargs="?", help="path to config file (default: bin/psws/config.json)")
parser.parse_known_args()

if len(sys.argv) > 1:
  config_file = sys.argv[1]
else:
  base = os.path.dirname(os.path.abspath(__file__))
  config_file = f"{base}/bin/psws/config.json"

if False:
  def catalog():
    return [{"id": "S000028"}, {"id": "S000082"}]

  del config['api']['scripts']['catalog']
  config['api']['functions'] = {"catalog": catalog}


hapiserver.run(config_file)
