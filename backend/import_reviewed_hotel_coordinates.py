"""Import only manually approved hotel coordinates. Default is dry run.
Run inside backend container with the review CSV mounted/copied to /app.
"""
import argparse
import csv
import math
from pathlib import Path
from database import SessionLocal
from models import Hotel



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file', type=Path)
    parser.add_argument('--apply', action='store_true', help='Commit approved records')
    args = parser.parse_args()
    if not args.csv_file.is_file():
        parser.error(f'File not found: {args.csv_file}')
    with args.csv_file.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    approvals = [r for r in rows if (r.get('reviewed') or '').strip().upper() == 'YES']
    print(f'Reviewed YES: {len(approvals)} / {len(rows)}')
    db = SessionLocal()
    pending = []
    errors = []
    try:
        seen = set()
        for r in approvals:
            try:
                hid = int(r['id'])
                if hid in seen:
                    raise ValueError('Duplicate hotel ID')
                seen.add(hid)
                hotel = db.get(Hotel, hid)
                if hotel is None:
                    raise ValueError('Hotel not in DB')
                if hotel.name.strip().casefold() != r['name'].strip().casefold():
                    raise ValueError('Hotel name differs from DB')
                if hotel.district.strip().casefold() != r['district'].strip().casefold():
                    raise ValueError('District differs from DB')
                if hotel.latitude is not None or hotel.longitude is not None:
                    raise ValueError('Existing coordinates present; will not overwrite')
                lat = float(r['candidate_latitude'])
                lon = float(r['candidate_longitude'])
                if not (math.isfinite(lat) and math.isfinite(lon) and 5.5 <= lat <= 10.1 and 79.3 <= lon <= 82.1):
                    raise ValueError('Coordinates outside expected Sri Lanka bounds')
                pending.append((hotel, lat, lon))
            except (KeyError, ValueError, TypeError) as exc:
                errors.append(f"ID {r.get('id')}: {exc}")
        for error in errors:
            print('SKIPPED:', error)
        print(f'Valid updates: {len(pending)}')
        if errors:
            print('Some approved rows failed checks; no changes committed.')
            db.rollback()
            return
        if not args.apply:
            print('DRY RUN ONLY. No database changes. Add --apply after reviewing the output.')
            return
        for hotel, lat, lon in pending:
            hotel.latitude = lat
            hotel.longitude = lon
        db.commit()
        print(f'COMMITTED {len(pending)} hotel coordinate updates.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
