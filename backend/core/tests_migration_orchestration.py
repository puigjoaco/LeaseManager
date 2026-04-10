import sys
from pathlib import Path

from django.test import SimpleTestCase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from migration.orchestration import read_backend_env_value, replace_database_name  # noqa: E402
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

