from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.management.local_evidence_paths import (
    validate_local_evidence_output_dir_path,
    validate_local_evidence_output_path,
)


class LocalEvidencePathTests(SimpleTestCase):
    def test_output_path_outside_repo_is_allowed(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            external_output = Path(temp_dir) / 'external' / 'audit.json'

            with self.settings(PROJECT_ROOT=str(repo_root)):
                validate_local_evidence_output_path(external_output)

    def test_output_path_inside_repo_outside_local_evidence_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            blocked_output = repo_root / 'docs' / 'audit.json'

            with self.settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'debe estar bajo local-evidence/'):
                    validate_local_evidence_output_path(blocked_output)

    def test_output_path_under_local_evidence_with_safe_relative_path_is_allowed(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            safe_output = repo_root / 'local-evidence' / 'stage6' / 'audit.json'

            with self.settings(PROJECT_ROOT=str(repo_root)):
                validate_local_evidence_output_path(safe_output)

    def test_output_path_under_local_evidence_with_sensitive_relative_path_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            sensitive_output = repo_root / 'local-evidence' / '11111111-1' / 'audit.json'

            with self.settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'ruta relativa no sensible'):
                    validate_local_evidence_output_path(sensitive_output)

    def test_output_dir_under_local_evidence_with_sensitive_relative_path_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            sensitive_output_dir = repo_root / 'local-evidence' / 'Socio Controlado 11.111.111-1' / 'package'

            with self.settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, '--output-dir debe usar una ruta relativa no sensible'):
                    validate_local_evidence_output_dir_path(sensitive_output_dir)
