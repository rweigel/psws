# Usage:
#   python data.py <id> <start> <stop>
# where <id> is the station ID, e.g., S000028 found in first column of catalog.csv
# <start> and <stop> are HAPI ISO date strings, e.g., 2023-03-22T00:00:00Z
#
# Example:
#   python data.py W2NAF 2025-10-20 2025-10-21
#
# Returns HAPI CSV stream to stdout
#
# Equivalent API response to:
#   hapi/data?dataset=<id>&start=<start>&stop=<stop>

import sys
import os
import re
import json
import datetime

# Read a file of formatted data points and convert to HAPI format    
# { "ts":"22 Mar 2023 20:23:13", "rt":27.00, "x":10.5296, "y":-8.8477, "z":47.7188, "rx":93, "ry":-78, "rz":423, "Tm": 49.6613 }
id, start, stop = sys.argv[1], sys.argv[2], sys.argv[3]
debug = True

if debug:
  print(f"ID: {id}, start: {start}, stop: {stop}")

def files_needed(id, start, stop):

  base = os.path.join("data", id)
  if not os.path.exists(base):
    print(f"Directory not found: {base}", file=sys.stderr)
    sys.exit(1)

  files = [f for f in os.listdir(base) if f.endswith("runmag.log")]
  files.sort()
  if not files:
    sys.exit(0)

  if debug:
    print(f"Found {len(files)} files that end with runmag.log in {base}")

  # Extract date from files with name of form w2naf-20251021-runmag.log
  date_re = re.compile(r'-[0-9]{8}-')

  files_needed = []
  # Convert from HAPI ISO date to YYYYMMDD, which is used in filenames
  start = start.replace("-", "")[0:8]
  stop = stop.replace("-", "")[0:8]

  if debug:
    print(f"Looking for files with data in range [{start}, {stop}]")

  for file in files:
    m = date_re.search(file)
    if m:
      file_date = m.group(0)[1:-1]  # YYYYMMDD
      if start <= file_date <= stop:
        files_needed.append(file)

  if debug:
    print(f"Found {len(files_needed)} files with data in range [{start}, {stop}]")

  return files_needed

def read_file(id, filename, start, stop):
  filepath = os.path.join("data", id, filename)
  # Row format:
  # {'ts': '21 Oct 2025 04:01:59', 'rt': 32.5, 'lt': 41.69, 'x': -45676.67, 'y': -13284.67, 'z': 16150.67, 'rx': -68515, 'ry': -19927, 'rz': 24226, 'Tm': 50236.2845}
  with open(filepath, 'r') as f:
    for line in f:
      entry = json.loads(line)
      ts = entry['ts']
      try:
        dt = datetime.datetime.strptime(ts, '%d %b %Y %H:%M:%S')
        entry['ts'] = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
      except Exception as e:
        if debug:
          print(f"Failed to parse ts '{ts}': {e}", file=sys.stderr)
      if entry['ts'][0:10] < start:
        continue
      if entry['ts'][0:10] >= stop:
        continue
      row = f"{entry['ts']},{entry['x']},{entry['y']},{entry['z']},"
      row += f"{entry['rx']},{entry['ry']},{entry['rz']},"
      row += f"{entry['rt']},{entry['lt']},{entry['Tm']}"
      print(row)

files = files_needed(id, start, stop)
for files in files:
  read_file(id, files, start, stop)
