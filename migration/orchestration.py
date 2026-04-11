from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / 'backend'
BACKEND_ENV_PATH = BACKEND_ROOT / '.env'


def read_backend_env_value(key: str, *, env_path: Path = BACKEND_ENV_PATH) -> str:
    if not env_path.exists():
        return ''
    prefix = f'{key}='
    for line in env_path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped.startswith(prefix):
            return stripped[len(prefix):]
    return ''


def replace_database_name(connection_url: str, database_name: str) -> str:
    parsed = urlsplit(connection_url)
    if not parsed.scheme:
        raise ValueError('La URL de conexión PostgreSQL es inválida o está vacía.')
    current_path = parsed.path or ''
    if current_path in ('', '/'):
        new_path = f'/{database_name}'
    else:
        segments = [segment for segment in current_path.split('/') if segment]
        if segments:
            segments[-1] = database_name
        else:
            segments = [database_name]
        new_path = '/' + '/'.join(segments)
    return urlunsplit((parsed.scheme, parsed.netloc, new_path, parsed.query, parsed.fragment))


def describe_database_target(connection_url: str) -> dict:
    if not connection_url:
        return {
            'database_url_host': '',
            'database_url_port': None,
            'database_name': '',
        }

    parsed = urlsplit(connection_url)
    return {
        'database_url_host': parsed.hostname or '',
        'database_url_port': parsed.port,
        'database_name': parsed.path.lstrip('/'),
    }


def postgres_admin_url(connection_url: str) -> str:
    return replace_database_name(connection_url, 'postgres')


def ensure_database_exists(connection_url: str, *, reuse_existing: bool = False) -> dict:
    parsed = urlsplit(connection_url)
    database_name = parsed.path.lstrip('/')
    if not database_name:
        raise ValueError('La URL de conexión PostgreSQL debe incluir nombre de base de datos.')

    admin_url = postgres_admin_url(connection_url)
    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            exists = cur.execute(
                'SELECT 1 FROM pg_database WHERE datname = %s',
                [database_name],
            ).fetchone() is not None
            if exists:
                if not reuse_existing:
                    raise ValueError(
                        f"La base de datos '{database_name}' ya existe. Usa otro nombre o habilita reuse_existing."
                    )
                return {'database_name': database_name, 'created': False}

            cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database_name)))
            return {'database_name': database_name, 'created': True}
