from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError

from core.reference_validation import is_non_sensitive_control_reference


def resolve_command_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def repo_root() -> Path:
    return Path(settings.PROJECT_ROOT).resolve()


def local_evidence_root() -> Path:
    return (repo_root() / 'local-evidence').resolve()


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def validate_local_evidence_output_path(
    output_path: Path,
    *,
    option_name: str = '--output',
    artifact_description: str = 'evidencia contable o tributaria',
) -> None:
    if not is_inside(output_path, repo_root()):
        return

    if not is_inside(output_path, local_evidence_root()):
        raise CommandError(
            f'Si {option_name} queda dentro del repo, debe estar bajo local-evidence/ '
            f'para no versionar {artifact_description}.'
        )

    relative_output_path = output_path.resolve().relative_to(local_evidence_root()).as_posix()
    if not is_non_sensitive_control_reference(relative_output_path):
        raise CommandError(f'{option_name} debe usar una ruta relativa no sensible bajo local-evidence/.')


def validate_required_local_evidence_output_path(
    output_path: Path,
    *,
    option_name: str = '--output',
    artifact_description: str = 'evidencia contable o tributaria',
) -> None:
    if not is_inside(output_path, local_evidence_root()):
        raise CommandError(
            f'{option_name} debe quedar bajo local-evidence/ para no exponer {artifact_description}.'
        )

    relative_output_path = output_path.resolve().relative_to(local_evidence_root()).as_posix()
    if not is_non_sensitive_control_reference(relative_output_path):
        raise CommandError(f'{option_name} debe usar una ruta relativa no sensible bajo local-evidence/.')


def validate_required_local_evidence_output_dir_path(
    output_dir: Path,
    *,
    option_name: str = '--output-dir',
    artifact_description: str = 'evidencia contable o tributaria',
) -> None:
    validate_required_local_evidence_output_path(
        output_dir,
        option_name=option_name,
        artifact_description=artifact_description,
    )


def validate_local_evidence_output_dir_path(
    output_dir: Path,
    *,
    option_name: str = '--output-dir',
    artifact_description: str = 'evidencia contable o tributaria',
) -> None:
    validate_local_evidence_output_path(
        output_dir,
        option_name=option_name,
        artifact_description=artifact_description,
    )
