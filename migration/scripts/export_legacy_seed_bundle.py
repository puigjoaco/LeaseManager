import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from migration.readers import fetch_legacy_rows  # noqa: E402
from migration.transformers import transform_legacy_bundle  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='Exporta un bundle canónico read-only desde la BD legacy.')
    parser.add_argument('--legacy-database-url', default=os.environ.get('LEGACY_DATABASE_URL', ''))
    parser.add_argument(
        '--output',
        default=os.environ.get('MIGRATION_BUNDLE_OUTPUT', ''),
        help='Ruta explicita de salida. Tambien puede venir de MIGRATION_BUNDLE_OUTPUT.',
    )
    args = parser.parse_args()

    if not args.legacy_database_url:
        raise SystemExit('LEGACY_DATABASE_URL es obligatorio para exportar el bundle.')
    if not args.output:
        raise SystemExit('--output o MIGRATION_BUNDLE_OUTPUT es obligatorio.')

    rows = fetch_legacy_rows(args.legacy_database_url)
    bundle = transform_legacy_bundle(rows)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True), encoding='utf-8')
    print(f'Bundle exportado en: {output_path}')


if __name__ == '__main__':
    main()

