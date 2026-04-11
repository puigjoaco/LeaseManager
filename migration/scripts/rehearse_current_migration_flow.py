from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / 'backend'

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from migration.orchestration import (
    describe_database_target,
    ensure_database_exists,
    read_backend_env_value,
    replace_database_name,
)


def run_command(command: list[str], *, env: dict[str, str], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def main():
    parser = argparse.ArgumentParser(
        description='Crea o reutiliza una base PostgreSQL y ejecuta el flujo validado actual de migración.'
    )
    parser.add_argument('database_name', help='Nombre de la base PostgreSQL destino.')
    parser.add_argument(
        '--bundle-path',
        default=str(PROJECT_ROOT / 'migration' / 'bundles' / 'legacy_seed_bundle.regenerated.current_2026-04-08.json'),
    )
    parser.add_argument('--reuse-existing', action='store_true')
    parser.add_argument('--output', default='')
    args = parser.parse_args()

    base_database_url = os.environ.get('DATABASE_URL') or read_backend_env_value('DATABASE_URL')
    if not base_database_url:
        raise SystemExit('No se pudo resolver DATABASE_URL base desde el entorno ni desde backend/.env.')

    target_database_url = replace_database_name(base_database_url, args.database_name)
    ensure_result = ensure_database_exists(target_database_url, reuse_existing=args.reuse_existing)

    env = os.environ.copy()
    env['DATABASE_URL'] = target_database_url

    migrate_stdout = run_command(
        [str(BACKEND_ROOT / '.venv' / 'Scripts' / 'python.exe'), 'manage.py', 'migrate', '--noinput'],
        env=env,
        cwd=BACKEND_ROOT,
    )
    runner_command = [
        str(BACKEND_ROOT / '.venv' / 'Scripts' / 'python.exe'),
        str(PROJECT_ROOT / 'migration' / 'scripts' / 'run_current_migration_flow.py'),
        args.bundle_path,
    ]
    if args.output:
        runner_command.extend(['--output', args.output])
    runner_stdout = run_command(
        runner_command,
        env=env,
        cwd=PROJECT_ROOT,
    )

    result = {
        'database_name': args.database_name,
        **describe_database_target(target_database_url),
        'database_created': ensure_result['created'],
        'bundle_path': args.bundle_path,
        'migrate_stdout': migrate_stdout,
        'runner_result': json.loads(runner_stdout),
    }
    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    print(rendered)


if __name__ == '__main__':
    main()
