# Usage:
#   python catalog.py
#
# Returns HAPI catalog information from catalog.csv in JSON format to stdout
#
# Equivalent API response to:
#   hapi/catalog

import csv
import json

catalog = []
with open('catalog.csv', 'r') as csvfile:
  reader = csv.reader(csvfile)
  for row in reader:
    if row[0].startswith('#'):
      continue
    catalog.append({"id": row[0].strip()})

print(json.dumps(catalog, indent=2))