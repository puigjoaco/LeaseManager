from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_BUNDLES_DIR = PROJECT_ROOT / 'migration' / 'bundles'


def resolve_output_path(raw_output_path: str) -> Path:
    output_path = Path(raw_output_path).expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    return output_path.resolve()


def validate_generated_migration_output_path(raw_output_path: str, artifact_label: str = 'artefactos de migracion') -> Path:
    output_path = resolve_output_path(raw_output_path)
    try:
        output_path.relative_to(PROJECT_ROOT)
    except ValueError:
        return output_path

    try:
        output_path.relative_to(MIGRATION_BUNDLES_DIR)
    except ValueError as exc:
        raise ValueError(
            f'Los {artifact_label} no pueden escribirse dentro del repo fuera de migration/bundles/. '
            'Usa una ruta externa o migration/bundles/, que esta ignorado por Git.'
        ) from exc

    return output_path


def validate_generated_bundle_output_path(raw_output_path: str) -> Path:
    return validate_generated_migration_output_path(raw_output_path, artifact_label='bundles legacy')
