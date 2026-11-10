# RF Analyzer lists

Curated lists that [RF Analyzer](https://github.com/demantz/RFAnalyzer) downloads, so corrections and
new entries reach every user without an app update.

| List | Source | Published as |
|---|---|---|
| Digital stations - presets of the digital modes (FT8 bands, APRS, LoRa networks, POCSAG, R09 cities, ...) | `digital_stations/*.yaml` | `digital_stations.json` |

The app ships a copy of each list for the first start without a network, and replaces it with the
published one when that is newer (`version`). Users can't edit these lists in the app; they copy an
entry to one of their own bookmark lists to change it.

## Digital stations

One file per mode. An entry:

```yaml
- id: r09-heidelberg          # stable, never change it: favorites are kept by it
  name: R09 Heidelberg
  mode: R09                   # FT8, AX25, ADSB, LORA, POCSAG, R09, RTTY, PSK31
  frequency: 152909800        # Hz; for FT8/PSK31 as the app tunes it (see the existing entries)
  bandwidth: 20000            # Hz, the demodulator's channel width
  countries: [DE]             # who gets it: countries (ISO 3166-1 alpha-2) or
  # regions: [1]              #   ITU regions; neither = everyone
  location: {lat: 49.40, lon: 8.69}   # optional: sorts the entry by distance for users with a position
  params:                     # optional, the demodulator settings the entry needs
    r09: {baudRate: 0}        # 0 = automatic
  notes: Where the values come from.
```

`params` blocks per mode: `rtty: {baudRate, frequencyShift, polarity}`, `pocsag: {baudRate}`,
`ax25: {baudRate: 300|1200|9600}`, `psk31: {baudRate}`, `r09: {baudRate}`,
`lora: {spreadingFactors, iqMode: AUTO|NORMAL|INVERTED}` - the values `tools/build.py` accepts are
listed there.

A user sees an entry when its `countries` contain their country, its `regions` their ITU region, or
it has neither.

## Building

```
pip install pyyaml
python3 tools/build.py            # validates, writes dist/digital_stations.json
```

GitHub Actions runs the same on every push and pull request and publishes `dist/` to GitHub Pages
from `main` (Settings → Pages → Source: GitHub Actions). The app's bundled copy is the same file:

```
python3 tools/build.py --out ../rfanalyzer_private/app/src/main/assets/lists
```
