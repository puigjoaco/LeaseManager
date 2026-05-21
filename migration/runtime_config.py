from __future__ import annotations

import json
import os


CURRENT_COMMUNITY_REPRESENTATIVE_RUT_ENV = 'MIGRATION_CURRENT_COMMUNITY_REPRESENTATIVE_RUT'
CURRENT_COMMUNITY_RECAUDADORA_ACCOUNT_NUMBER_ENV = 'MIGRATION_CURRENT_COMMUNITY_RECAUDADORA_ACCOUNT_NUMBER'
KNOWN_SOCIO_ACCOUNT_OWNER_RUTS_ENV = 'MIGRATION_KNOWN_SOCIO_ACCOUNT_OWNER_RUTS'


def _read_env(name: str) -> str:
    return os.environ.get(name, '').strip()


def get_current_community_representative_rut() -> str:
    return _read_env(CURRENT_COMMUNITY_REPRESENTATIVE_RUT_ENV)


def require_current_community_representative_rut() -> str:
    value = get_current_community_representative_rut()
    if not value:
        raise ValueError(f'{CURRENT_COMMUNITY_REPRESENTATIVE_RUT_ENV} debe estar configurado para resolver comunidades actuales.')
    return value


def get_current_community_recaudadora_account_number() -> str:
    return _read_env(CURRENT_COMMUNITY_RECAUDADORA_ACCOUNT_NUMBER_ENV)


def require_current_community_recaudadora_account_number() -> str:
    value = get_current_community_recaudadora_account_number()
    if not value:
        raise ValueError(
            f'{CURRENT_COMMUNITY_RECAUDADORA_ACCOUNT_NUMBER_ENV} debe estar configurado para resolver mandatos comunitarios actuales.'
        )
    return value


def get_known_socio_account_owner_ruts() -> dict[str, str]:
    raw = _read_env(KNOWN_SOCIO_ACCOUNT_OWNER_RUTS_ENV)
    if not raw:
        return {}

    if raw.startswith('{'):
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError(f'{KNOWN_SOCIO_ACCOUNT_OWNER_RUTS_ENV} debe ser un objeto JSON account->rut.')
        return {str(account): str(rut) for account, rut in parsed.items()}

    mapping: dict[str, str] = {}
    for pair in raw.split(';'):
        if not pair.strip():
            continue
        if '=' not in pair:
            raise ValueError(f'{KNOWN_SOCIO_ACCOUNT_OWNER_RUTS_ENV} debe usar pares account=rut separados por ;.')
        account, rut = pair.split('=', 1)
        mapping[account.strip()] = rut.strip()
    return mapping
