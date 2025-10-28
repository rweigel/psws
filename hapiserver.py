import os
import sys

import hapiserver
import argparse
parser = argparse.ArgumentParser(description="HAPI server")
help = "Path to configuration file (default: ./bin/psws/config.json)"
parser.add_argument("config", nargs="?", help=help)
parser.parse_known_args()

if len(sys.argv) > 1:
  config_file = sys.argv[1]
else:
  base = os.path.dirname(os.path.abspath(__file__))
  config_file = f"{base}/bin/psws/config.json"


hapiserver.run(config_file)


