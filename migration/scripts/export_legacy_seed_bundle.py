import argparse
import json
import os
from pathlib import Path

from migration.readers import fetch_legacy_rows
from migration.transformers import transform_legacy_bundle

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'migration' / 'bundles'


def main():
    parser = argparse.ArgumentParser(description='Exporta un bundle canónico read-only desde la BD legacy.')
    parser.add_argument('--legacy-database-url', default=os.environ.get('LEGACY_DATABASE_URL', ''))
    parser.add_argument('--output', default='')
    args = parser.parse_args()

    if not args.legacy_database_url:
        raise SystemExit('LEGACY_DATABASE_URL es obligatorio para exportar el bundle.')

    rows = fetch_legacy_rows(args.legacy_database_url)
    bundle = transform_legacy_bundle(rows)

    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR / 'legacy_seed_bundle.json'
    output_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True), encoding='utf-8')
    print(f'Bundle exportado en: {output_path}')


if __name__ == '__main__':
    main()

