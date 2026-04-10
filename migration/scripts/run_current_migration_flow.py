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

from migration.importers import run_current_migration_flow  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description='Ejecuta el flujo validado actual: import -> resolve comunidades -> import -> import.'
    )
    parser.add_argument('bundle_path')
    parser.add_argument('--output', default='')
    parser.add_argument('--no-assert-final-state', action='store_true')
    args = parser.parse_args()

    bundle = json.loads(Path(args.bundle_path).read_text(encoding='utf-8'))
    result = run_current_migration_flow(bundle)
    rendered = json.dumps(result, indent=2, ensure_ascii=True)

    if args.output:
        Path(args.output).write_text(rendered, encoding='utf-8')

    print(rendered)
    if not args.no_assert_final_state and not result['validation']['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

