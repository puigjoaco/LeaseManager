import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / 'backend'

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leasemanager_api.settings')

import django

django.setup()

from migration.importers import import_bundle  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='Importa al backend nuevo un bundle canónico legado.')
    parser.add_argument('bundle_path')
    args = parser.parse_args()

    bundle = json.loads(Path(args.bundle_path).read_text(encoding='utf-8'))
    report = import_bundle(bundle)
    print(json.dumps({'created': report.created, 'updated': report.updated, 'skipped': report.skipped}, indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()

