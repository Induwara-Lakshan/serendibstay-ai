"""Generate REVIEWABLE geocoding candidates; does not update the database.

Requires a Geoapify API key. Uses the Geoapify Geocoding API, with pacing,
retry and a local cache so an interrupted run can resume safely.
"""
import csv
import difflib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SOURCE = Path(sys.argv[1] if len(sys.argv) > 1 else 'hotel_locations.csv')
OUTPUT = Path('hotel_geocoding_review.csv')
CACHE = Path('hotel_geocoding_cache.json')
API_KEY = os.getenv('GEOAPIFY_API_KEY', '').strip()
API_URL = 'https://api.geoapify.com/v1/geocode/search'
FIELDS = ['id', 'name', 'address', 'district', 'existing_latitude', 'existing_longitude', 'candidate_latitude', 'candidate_longitude', 'matched_address', 'matched_name', 'confidence', 'status', 'reviewed', 'source']


def normalized(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s or '').lower()).strip()


def search(query):
    params = urllib.parse.urlencode({'text': query, 'filter': 'countrycode:lk', 'limit': 5, 'format': 'json', 'apiKey': API_KEY})
    url = f'{API_URL}?{params}'
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'SerendibStayGeocodingReview/1.0'})
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.load(response).get('results', [])
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise RuntimeError('Invalid API key or Geoapify quota/permissions issue') from exc
            if exc.code == 429 or 500 <= exc.code < 600:
                time.sleep(3 * (attempt + 1))
                continue
            raise
        except (TimeoutError, urllib.error.URLError):
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))
    return []


def select_candidate(results, name, district):
    choices = []
    for result in results:
        lat, lon = result.get('lat'), result.get('lon')
        if not isinstance(lat, (float, int)) or not isinstance(lon, (float, int)):
            continue
        if not (5.8 <= lat <= 10.1 and 79.4 <= lon <= 82.2):
            continue
        label = str(result.get('name') or result.get('address_line1') or '')
        formatted = str(result.get('formatted') or '')
        name_score = difflib.SequenceMatcher(None, normalized(name), normalized(label)).ratio()
        # Geoapify's general geocoder may match only the road or town.
        # Keep even high-scoring candidates in the manual-review queue.
        district_present = normalized(district) in normalized(formatted)
        score = round(name_score * 0.85 + (0.15 if district_present else 0), 3)
        choices.append((score, result, label, formatted))
    return max(choices, key=lambda x: x[0]) if choices else None


def main():
    if not API_KEY:
        raise SystemExit('Set GEOAPIFY_API_KEY in your terminal first. Never paste the key in chat.')
    if not SOURCE.exists():
        raise SystemExit(f'Input CSV not found: {SOURCE.resolve()}')
    with SOURCE.open(newline='', encoding='utf-8-sig') as fh:
        hotels = list(csv.DictReader(fh))
    if not hotels or not {'id', 'name', 'address', 'district', 'latitude', 'longitude'}.issubset(hotels[0]):
        raise SystemExit('CSV must contain id,name,address,district,latitude,longitude')
    cache = json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {}
    output_rows = []
    for index, hotel in enumerate(hotels, 1):
        key = str(hotel['id']).strip()
        row = {'id': key, 'name': hotel['name'], 'address': hotel['address'], 'district': hotel['district'],
               'existing_latitude': hotel['latitude'], 'existing_longitude': hotel['longitude'],
               'candidate_latitude': '', 'candidate_longitude': '', 'matched_address': '', 'matched_name': '',
               'confidence': '', 'status': '', 'reviewed': '', 'source': ''}
        if hotel['latitude'].strip() and hotel['longitude'].strip():
            row.update({'candidate_latitude': hotel['latitude'], 'candidate_longitude': hotel['longitude'],
                        'status': 'EXISTING_COORDINATES', 'source': 'database'})
        else:
            if key not in cache:
                query = ', '.join(filter(None, [hotel['name'], hotel['address'], hotel['district'], 'Sri Lanka']))
                print(f'[{index}/{len(hotels)}] Searching: {hotel["name"]}', flush=True)
                try:
                    cache[key] = search(query)
                except Exception as exc:
                    print(f'  Search failed: {type(exc).__name__}: {exc}', file=sys.stderr)
                    cache[key] = {'error': str(exc)}
                CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
                time.sleep(1.1)
            results = cache[key]
            if isinstance(results, dict) and 'error' in results:
                row['status'] = 'SEARCH_ERROR'
            else:
                match = select_candidate(results, hotel['name'], hotel['district'])
                if match:
                    score, candidate, label, formatted = match
                    row.update({'candidate_latitude': candidate['lat'], 'candidate_longitude': candidate['lon'],
                                'matched_address': formatted, 'matched_name': label, 'confidence': score,
                                'status': 'REVIEW_REQUIRED', 'source': 'Geoapify geocoding'})
                else:
                    row['status'] = 'NOT_FOUND'
        output_rows.append(row)
        # Write after each row, to preserve progress if interrupted.
        with OUTPUT.open('w', newline='', encoding='utf-8-sig') as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(output_rows)
    print(f'Finished: {len(output_rows)} hotels. Review {OUTPUT.resolve()} before updating the DB.')
    print('No database changes were made.')


if __name__ == '__main__':
    main()
