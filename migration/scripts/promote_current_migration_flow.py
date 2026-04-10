from __future__ import annotations

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

from django.core.management import call_command  # noqa: E402

from migration.importers import (  # noqa: E402
    collect_migration_state_snapshot,
    run_current_migration_flow,
    validate_current_migration_empty_state,
)


def main():
    parser = argparse.ArgumentParser(
        description='Migra un target PostgreSQL ya existente y ejecuta el flujo validado actual.'
    )
    parser.add_argument('bundle_path')
    parser.add_argument('--output', default='')
    parser.add_argument('--allow-non-empty', action='store_true')
    args = parser.parse_args()

    bundle = json.loads(Path(args.bundle_path).read_text(encoding='utf-8'))
    call_command('migrate', interactive=False)
    pre_state = collect_migration_state_snapshot()
    pre_validation = validate_current_migration_empty_state(pre_state)

    if not args.allow_non_empty and not pre_validation['ok']:
        result = {
            'pre_state': pre_state,
            'pre_validation': pre_validation,
            'aborted': True,
            'reason': 'Target PostgreSQL no esta vacio despues de migrate.',
        }
        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if args.output:
            Path(args.output).write_text(rendered, encoding='utf-8')
        print(rendered)
        raise SystemExit(1)

    runner_result = run_current_migration_flow(bundle)
    result = {
        'pre_state': pre_state,
        'pre_validation': pre_validation,
        'runner_result': runner_result,
    }
    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).write_text(rendered, encoding='utf-8')
    print(rendered)
    if not runner_result['validation']['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

