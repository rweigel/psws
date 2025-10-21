# Usage:
#   python info.py <id>
# where <id> is the station ID, e.g., S000028 found in first column of catalog.csv
#
# Example:
#   python info.py S000028
#
# Returns HAPI info JSON stdout
#
# Equivalent API response to:
#   hapi/info?dataset=<id>

import sys
import csv
import json

def get_catalog():
  catalog = {}
  with open('catalog.csv', 'r') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
      if row[0].startswith('#'):
        continue
      catalog[row[0].strip()] = {
        'nickname': row[1].strip(),
        'startDateTime': row[2].strip(),
        'stopDateTime': row[3].strip(),
        'lat': float(row[4]),
        'long': float(row[5]),
        'elevation': float(row[6])
      }
  return catalog

catalog = get_catalog()

with open('info.template.json', 'r') as f:
  info = json.load(f)

id = sys.argv[1]
if id not in catalog:
  print(f"ID {id} not found in catalog", file=sys.stderr)
  sys.exit(1)

info['startDate'] = catalog[id]['startDateTime']
info['stopDate'] = catalog[id]['stopDateTime']
info['geoLocation'] = [catalog[id]['lat'], catalog[id]['long'], catalog[id]['elevation']]

print(json.dumps(info, indent=2))
