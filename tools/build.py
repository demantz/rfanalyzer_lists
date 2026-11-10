#!/usr/bin/env python3
"""Validates the list sources and builds what RF Analyzer downloads.

    python3 tools/build.py [--out DIR] [--version N]

Reads digital_stations/*.yaml and writes DIR/digital_stations.json (default DIR: dist). The version
is the newest commit's time (seconds) unless given - the app keeps whichever of its bundled copy and
the downloaded file has the higher version. Exits with 1 and lists every problem if a source is invalid.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

import yaml

FORMAT = 1
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# DemodulationMode (rfanalyzer_private ui/tabs/DemodulationTab.kt): the digital modes and their channel width limits
MODES = {
    'FT8': (3000, 3000), 'AX25': (300, 25000), 'ADSB': (1_000_000, 1_000_000), 'LORA': (31250, 500000),
    'POCSAG': (12500, 25000), 'R09': (20000, 20000), 'RTTY': (85, 850), 'PSK31': (50, 200),
}
# DemodulationParameters (rfanalyzer_private database/StationDao.kt): which block each mode may carry, and its fields
PARAMS = {
    'rtty': ('RTTY', {'baudRate': (0.0, 45.45, 50.0, 75.0, 100.0), 'frequencyShift': (0.0, 85.0, 170.0, 450.0, 850.0),
                      'polarity': ('AUTO', 'NORMAL', 'REVERSED')}),
    'pocsag': ('POCSAG', {'baudRate': (0, 512, 1200, 2400)}),
    'ax25': ('AX25', {'baudRate': (300, 1200, 9600)}),
    'psk31': ('PSK31', {'baudRate': (0.0, 31.25, 62.5, 125.0)}),
    'r09': ('R09', {'baudRate': (0, 1200, 2400)}),
    'lora': ('LORA', {'spreadingFactors': None, 'iqMode': ('AUTO', 'NORMAL', 'INVERTED')}),
}
FIELDS = ('id', 'name', 'mode', 'frequency', 'bandwidth', 'regions', 'countries', 'location', 'params', 'notes')
ID_PATTERN = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
COUNTRY_PATTERN = re.compile(r'^[A-Z]{2}$')


def validate(entry, where):
    problems = []
    def bad(msg):
        problems.append(f"{where}: {msg}")
    for field in entry:
        if field not in FIELDS:
            bad(f"unknown field '{field}'")
    for field in ('id', 'name', 'mode', 'frequency', 'bandwidth'):
        if field not in entry:
            bad(f"'{field}' missing")
    if problems:
        return problems
    if not ID_PATTERN.match(str(entry['id'])):
        bad(f"id '{entry['id']}' must be lower-case words joined by '-'")
    mode = entry['mode']
    if mode not in MODES:
        bad(f"mode '{mode}' is not one of {', '.join(MODES)}")
    if not isinstance(entry['frequency'], int) or entry['frequency'] <= 0:
        bad("frequency must be a positive integer (Hz)")
    width = entry['bandwidth']
    if mode in MODES and not (isinstance(width, int) and MODES[mode][0] <= width <= MODES[mode][1]):
        bad(f"bandwidth {width} outside {mode}'s {MODES[mode][0]}..{MODES[mode][1]} Hz")
    if 'regions' in entry and 'countries' in entry:
        bad("give regions or countries, not both")
    for region in entry.get('regions', []):
        if region not in (1, 2, 3):
            bad(f"region {region} is not an ITU region (1, 2, 3)")
    for country in entry.get('countries', []):
        if not COUNTRY_PATTERN.match(str(country)):
            bad(f"country '{country}' is not an ISO 3166-1 alpha-2 code")
    if 'location' in entry:
        loc = entry['location']
        if not (isinstance(loc, dict) and set(loc) == {'lat', 'lon'} and -90 <= loc['lat'] <= 90 and -180 <= loc['lon'] <= 180):
            bad("location must be {lat, lon} in degrees")
    for block, values in entry.get('params', {}).items():
        if block not in PARAMS:
            bad(f"unknown params block '{block}'")
            continue
        block_mode, fields = PARAMS[block]
        if block_mode != mode:
            bad(f"params block '{block}' belongs to {block_mode}, not {mode}")
        for name, value in values.items():
            if name not in fields:
                bad(f"unknown field '{block}.{name}'")
            elif fields[name] is not None and value not in fields[name]:
                bad(f"{block}.{name} = {value!r} is not one of {fields[name]}")
    return problems


def head_commit_time():
    try:
        return int(subprocess.check_output(['git', 'log', '-1', '--format=%ct'], cwd=ROOT, text=True).strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default=os.path.join(ROOT, 'dist'))
    parser.add_argument('--version', type=int, default=None)
    args = parser.parse_args()

    problems, stations, seen = [], [], {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'digital_stations', '*.yaml'))):
        name = os.path.relpath(path, ROOT)
        entries = yaml.safe_load(open(path, encoding='utf-8')) or []
        if not isinstance(entries, list):
            problems.append(f"{name}: must be a list of stations")
            continue
        for index, entry in enumerate(entries):
            where = f"{name} #{index + 1} ({entry.get('id', '?') if isinstance(entry, dict) else '?'})"
            if not isinstance(entry, dict):
                problems.append(f"{where}: must be a mapping")
                continue
            problems += validate(entry, where)
            if entry.get('id') in seen:
                problems.append(f"{where}: id also used in {seen[entry['id']]}")
            seen[entry.get('id')] = where
            stations.append({field: entry[field] for field in FIELDS if field in entry})
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        sys.exit(1)

    stations.sort(key=lambda s: (list(MODES).index(s['mode']), s['frequency'], s['id']))
    version = args.version if args.version is not None else head_commit_time()
    os.makedirs(args.out, exist_ok=True)
    out = os.path.join(args.out, 'digital_stations.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'format': FORMAT, 'version': version, 'stations': stations}, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')
    print(f"{out}: {len(stations)} stations, version {version}")


if __name__ == '__main__':
    main()
