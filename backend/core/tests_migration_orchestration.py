import sys
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from migration.scripts import (  # noqa: E402
    export_legacy_seed_bundle,
    promote_current_migration_flow,
    rehearse_current_migration_flow,
    run_current_migration_flow,
    verify_current_migration_target,
)
from migration.orchestration import describe_database_target, read_backend_env_value, replace_database_name  # noqa: E402
from migration.output_paths import validate_generated_bundle_output_path  # noqa: E402
from migration.importers import (  # noqa: E402
    validate_current_migration_empty_state,
    validate_current_migration_state,
)


class MigrationOrchestrationTests(SimpleTestCase):
    def test_replace_database_name_swaps_last_path_segment(self):
        original = 'postgresql://leasemanager:leasemanager@localhost:5433/leasemanager_migration_run_20260409_v7'
        replaced = replace_database_name(original, 'leasemanager_migration_run_test')
        self.assertEqual(
            replaced,
            'postgresql://leasemanager:leasemanager@localhost:5433/leasemanager_migration_run_test',
        )

    def test_read_backend_env_value_returns_empty_when_file_missing(self):
        missing_path = PROJECT_ROOT / 'backend' / '.env.does-not-exist'
        self.assertEqual(read_backend_env_value('DATABASE_URL', env_path=missing_path), '')

    def test_describe_database_target_redacts_credentials_and_keeps_host_metadata(self):
        description = describe_database_target(
            'postgresql://postgres.secret-user:super-secret-password@aws-1-sa-east-1.pooler.supabase.com:5432/postgres'
        )
        self.assertEqual(
            description,
            {
                'database_url_host': 'aws-1-sa-east-1.pooler.supabase.com',
                'database_url_port': 5432,
                'database_name': 'postgres',
            },
        )

    def test_describe_database_target_returns_empty_metadata_when_url_is_missing(self):
        self.assertEqual(
            describe_database_target(''),
            {
                'database_url_host': '',
                'database_url_port': None,
                'database_name': '',
            },
        )

    def test_generated_bundle_output_allows_external_paths(self):
        output_path = validate_generated_bundle_output_path(
            str(PROJECT_ROOT.parent / 'controlled-bundles' / 'bundle.json')
        )
        self.assertEqual(output_path, (PROJECT_ROOT.parent / 'controlled-bundles' / 'bundle.json').resolve())

    def test_generated_bundle_output_allows_ignored_bundle_dir(self):
        output_path = validate_generated_bundle_output_path(
            str(PROJECT_ROOT / 'migration' / 'bundles' / 'bundle.local.json')
        )
        self.assertEqual(output_path, (PROJECT_ROOT / 'migration' / 'bundles' / 'bundle.local.json').resolve())

    def test_generated_bundle_output_rejects_tracked_repo_paths(self):
        with self.assertRaisesMessage(ValueError, 'migration/bundles'):
            validate_generated_bundle_output_path(str(PROJECT_ROOT / 'docs' / 'bundle.json'))

    def test_export_bundle_rejects_repo_output_before_legacy_read(self):
        argv = [
            'export_legacy_seed_bundle.py',
            '--legacy-database-url',
            'postgresql://legacy.example/db',
            '--output',
            str(PROJECT_ROOT / 'docs' / 'bundle.json'),
        ]
        with (
            patch.object(sys, 'argv', argv),
            patch.object(export_legacy_seed_bundle, 'fetch_legacy_rows') as fetch_rows,
        ):
            with self.assertRaisesMessage(ValueError, 'migration/bundles'):
                export_legacy_seed_bundle.main()
        fetch_rows.assert_not_called()

    def test_run_current_rejects_repo_output_before_bundle_read(self):
        argv = [
            'run_current_migration_flow.py',
            str(PROJECT_ROOT / 'migration' / 'bundles' / 'bundle.local.json'),
            '--output',
            str(PROJECT_ROOT / 'docs' / 'migration-report.json'),
        ]
        with (
            patch.object(sys, 'argv', argv),
            patch.object(run_current_migration_flow.Path, 'read_text') as read_text,
            patch.object(run_current_migration_flow, 'run_current_migration_flow') as runner,
        ):
            with self.assertRaisesMessage(ValueError, 'migration/bundles'):
                run_current_migration_flow.main()
        read_text.assert_not_called()
        runner.assert_not_called()

    def test_promote_current_rejects_repo_output_before_migrate(self):
        argv = [
            'promote_current_migration_flow.py',
            str(PROJECT_ROOT / 'migration' / 'bundles' / 'bundle.local.json'),
            '--output',
            str(PROJECT_ROOT / 'docs' / 'promote-report.json'),
        ]
        with (
            patch.object(sys, 'argv', argv),
            patch.object(promote_current_migration_flow.Path, 'read_text') as read_text,
            patch.object(promote_current_migration_flow, 'call_command') as call_command,
        ):
            with self.assertRaisesMessage(ValueError, 'migration/bundles'):
                promote_current_migration_flow.main()
        read_text.assert_not_called()
        call_command.assert_not_called()

    def test_verify_current_rejects_repo_output_before_snapshot_read(self):
        argv = [
            'verify_current_migration_target.py',
            '--output',
            str(PROJECT_ROOT / 'docs' / 'verify-report.json'),
        ]
        with (
            patch.object(sys, 'argv', argv),
            patch.object(verify_current_migration_target, 'collect_snapshot') as collect_snapshot,
        ):
            with self.assertRaisesMessage(ValueError, 'migration/bundles'):
                verify_current_migration_target.main()
        collect_snapshot.assert_not_called()

    def test_rehearse_current_rejects_repo_output_before_database_work(self):
        argv = [
            'rehearse_current_migration_flow.py',
            'leasemanager_migration_run_test',
            '--bundle-path',
            str(PROJECT_ROOT / 'migration' / 'bundles' / 'bundle.local.json'),
            '--output',
            str(PROJECT_ROOT / 'docs' / 'rehearse-report.json'),
        ]
        with (
            patch.object(sys, 'argv', argv),
            patch.object(rehearse_current_migration_flow, 'read_backend_env_value') as read_env,
            patch.object(rehearse_current_migration_flow, 'ensure_database_exists') as ensure_database,
        ):
            with self.assertRaisesMessage(ValueError, 'migration/bundles'):
                rehearse_current_migration_flow.main()
        read_env.assert_not_called()
        ensure_database.assert_not_called()

    def test_validate_current_migration_state_accepts_expected_snapshot(self):
        snapshot = {
            'comunidades': 16,
            'participaciones_comunidad': 70,
            'mandatos': 66,
            'contratos': 56,
            'periodos': 748,
            'manual_resolutions_abiertas': 0,
        }
        result = validate_current_migration_state(snapshot)
        self.assertTrue(result['ok'])
        self.assertEqual(result['mismatches'], {})

    def test_validate_current_migration_state_reports_mismatches(self):
        snapshot = {
            'comunidades': 15,
            'participaciones_comunidad': 70,
            'mandatos': 65,
            'contratos': 56,
            'periodos': 747,
            'manual_resolutions_abiertas': 1,
        }
        result = validate_current_migration_state(snapshot)
        self.assertFalse(result['ok'])
        self.assertEqual(
            result['mismatches'],
            {
                'comunidades': {'expected': 16, 'actual': 15},
                'mandatos': {'expected': 66, 'actual': 65},
                'periodos': {'expected': 748, 'actual': 747},
                'manual_resolutions_abiertas': {'expected': 0, 'actual': 1},
            },
        )

    def test_validate_current_migration_empty_state_accepts_zero_snapshot(self):
        snapshot = {
            'socios': 0,
            'empresas': 0,
            'comunidades': 0,
            'participaciones_comunidad': 0,
            'participaciones_empresa': 0,
            'propiedades': 0,
            'cuentas_recaudadoras': 0,
            'mandatos': 0,
            'arrendatarios': 0,
            'contratos': 0,
            'periodos': 0,
            'manual_resolutions_abiertas': 0,
            'manual_resolutions_resueltas': 0,
        }
        result = validate_current_migration_empty_state(snapshot)
        self.assertTrue(result['ok'])
        self.assertEqual(result['mismatches'], {})

