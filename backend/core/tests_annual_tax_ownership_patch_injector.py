import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from core.annual_tax_controlled_db_load import CONTROLLED_DB_LOAD_SCHEMA_VERSION
from core.annual_tax_controlled_package_template import CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION
from core.annual_tax_ownership_patch_injector import (
    OWNERSHIP_PATCH_INJECTION_SCHEMA_VERSION,
    inject_annual_tax_ownership_patch_into_controlled_package,
)
from core.annual_tax_ownership_patch_validator import OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION
from core.annual_tax_ownership_snapshot_template import OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION


class AnnualTaxOwnershipPatchInjectorTests(SimpleTestCase):
    def _template(self) -> dict:
        return {
            'schema_version': OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'source_review_hash': 'a' * 64,
            'responsible_ref': 'codex-controlled-review',
            'approval_ref': 'approval-controlled',
            'safety': {
                'stores_rut_values': False,
                'stores_person_names': False,
            },
            'candidate_sources': [
                {
                    'path_ref': 'file-path-sha256:' + 'b' * 64,
                    'sha256': 'c' * 64,
                    'document_kind': 'constitution_deed',
                    'review_status': 'manual_review_required_legal_candidate',
                    'path_context_tags': ['constitution'],
                    'evidence_ref_suggestion': 'ownership-evidence-' + 'c' * 12,
                    'requires_ocr_or_manual_read': True,
                }
            ],
            'ownership_patch_template': {
                'source_ref': 'ownership-review-2024-controlled',
                'as_of': '2024-12-31',
                'participants': [],
            },
            'decision': {
                'can_patch_controlled_db_load_package_after_manual_completion': True,
                'ready_for_controlled_db_load': False,
            },
        }

    def _valid_patch(self) -> dict:
        return {
            'schema_version': OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'responsible_ref': 'responsable-controlado',
            'approval_ref': 'aprobacion-controlada',
            'ownership': self._ownership_snapshot(),
        }

    def _ownership_snapshot(self) -> dict:
        return {
            'source_ref': 'ownership-structure-2024-controlled',
            'as_of': '2024-12-31',
            'participants': [
                {
                    'participant_type': 'socio',
                    'participant_ref': 'socio-controlled-one',
                    'name': 'Socio Controlado Uno',
                    'rut': '11111111-1',
                    'percentage': '60.00',
                    'vigente_desde': '2024-01-01',
                    'vigente_hasta': None,
                    'evidence_ref': 'ownership-evidence-controlled-one',
                },
                {
                    'participant_type': 'socio',
                    'participant_ref': 'socio-controlled-two',
                    'name': 'Socio Controlado Dos',
                    'rut': '22222222-2',
                    'percentage': '40.00',
                    'vigente_desde': '2024-01-01',
                    'vigente_hasta': None,
                    'evidence_ref': 'ownership-evidence-controlled-two',
                },
            ],
        }

    def _ownership_review_handoff(self) -> dict:
        return {
            'schema_version': CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION,
            'source_checklist_hash': 'b' * 64,
            'reviewable_candidates_total': 10,
            'rendered_candidates_total': 10,
            'validation_present': True,
            'participants_count': 2,
            'percentage_total': '100.00',
            'blocking_items_total': 0,
            'blocking_item_keys': [],
            'validation_blockers': [],
            'ready_for_manual_review': True,
            'ready_for_controlled_db_load': True,
            'can_inject_ownership_into_controlled_package': True,
            'next_action': 'inject_validated_ownership_snapshot_into_package_ownership',
            'writes_database': False,
            'stores_source_paths': False,
            'stores_person_names': False,
            'stores_rut_values': False,
            'auto_generates_ownership': False,
        }

    def _complete_package(self, *, include_ownership=False) -> dict:
        package = {
            'schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'source_manifest_hash': 'a' * 64,
            'responsible_ref': 'responsable-controlado',
            'approval_ref': 'aprobacion-controlada',
            'expected_outputs_used_as_inputs': False,
            'annual_input_source_refs': {
                'annual_ledger_input': [
                    {
                        'path_ref': 'libro-diario-mayor-anual-controlado',
                        'category': 'annual_ledger_input',
                        'artifact_key': 'annual_ledger',
                    }
                ],
            },
            'ownership_review': self._ownership_review_handoff(),
            'months': [
                {
                    'month': month,
                    'source_ref': f'ac2024-month-{month:02d}-controlled',
                    'ledger': {
                        'libro_diario_ref': f'libro-diario-2024-{month:02d}-controlled',
                        'libro_mayor_ref': f'libro-mayor-2024-{month:02d}-controlled',
                        'asientos_count': 10,
                        'cuentas_count': 25,
                        'total_debe': '1000.00',
                        'total_haber': '1000.00',
                    },
                    'balance': {
                        'balance_ref': f'balance-comprobacion-2024-{month:02d}-controlled',
                        'total_debe': '1000.00',
                        'total_haber': '1000.00',
                        'cuadrado': True,
                    },
                    'obligations': [
                        {
                            'tipo': 'PPM',
                            'base_imponible': '1000.00',
                            'monto_calculado': '10.00',
                        }
                    ],
                    'f29': {
                        'estado_preparacion': 'preparado',
                        'borrador_ref': f'f29-2024-{month:02d}-controlled',
                        'resumen': {'declarado': True},
                    },
                    'payroll': {
                        'source_ref': '',
                        'has_movements': False,
                        'resumen': {'reviewed': True},
                    },
                }
                for month in range(1, 13)
            ],
        }
        if include_ownership:
            package['ownership'] = self._ownership_snapshot()
        return package

    def test_inject_valid_patch_adds_ownership_and_reaudits_generation(self):
        result = inject_annual_tax_ownership_patch_into_controlled_package(
            package_payload=self._complete_package(),
            template=self._template(),
            patch=self._valid_patch(),
        )
        rendered_validation = json.dumps(result['validation'], ensure_ascii=True)

        self.assertEqual(result['schema_version'], OWNERSHIP_PATCH_INJECTION_SCHEMA_VERSION)
        self.assertEqual(result['package']['ownership']['participants'][0]['name'], 'Socio Controlado Uno')
        self.assertEqual(result['package']['ownership']['participants'][0]['rut'], '11111111-1')
        self.assertTrue(result['readiness']['ready_for_db_writer'])
        self.assertTrue(result['readiness']['ready_for_annual_generation'])
        self.assertEqual(result['readiness']['annual_generation_blockers'], [])
        self.assertNotIn('ownership_review_ready_requires_package_ownership', result['readiness']['warnings'])
        self.assertEqual(
            result['package']['ownership_review']['next_action'],
            'package_ownership_injected_reaudit_readiness',
        )
        self.assertTrue(result['safety']['output_contains_ownership_pii'])
        self.assertFalse(result['safety']['writes_database'])
        self.assertFalse(result['safety']['final_tax_calculation'])
        self.assertNotIn('Socio Controlado Uno', rendered_validation)
        self.assertNotIn('11111111-1', rendered_validation)

    def test_invalid_patch_is_refused_before_injection(self):
        patch = self._valid_patch()
        patch['ownership']['participants'][1]['percentage'] = '39.00'

        with self.assertRaisesMessage(ValueError, 'Ownership patch no listo'):
            inject_annual_tax_ownership_patch_into_controlled_package(
                package_payload=self._complete_package(),
                template=self._template(),
                patch=patch,
            )

    def test_participant_not_active_on_snapshot_date_is_refused_before_injection(self):
        patch = self._valid_patch()
        patch['ownership']['participants'][1]['vigente_hasta'] = '2024-09-30'

        with self.assertRaisesMessage(ValueError, 'Ownership patch no listo'):
            inject_annual_tax_ownership_patch_into_controlled_package(
                package_payload=self._complete_package(),
                template=self._template(),
                patch=patch,
            )

    def test_existing_ownership_requires_explicit_replace(self):
        package = self._complete_package(include_ownership=True)

        with self.assertRaisesMessage(ValueError, 'package.ownership ya existe'):
            inject_annual_tax_ownership_patch_into_controlled_package(
                package_payload=package,
                template=self._template(),
                patch=self._valid_patch(),
            )

        result = inject_annual_tax_ownership_patch_into_controlled_package(
            package_payload=package,
            template=self._template(),
            patch=self._valid_patch(),
            replace_existing=True,
        )

        self.assertTrue(result['summary']['ownership_injected'])
        self.assertTrue(result['summary']['ready_for_annual_generation'])

    def test_command_writes_full_output_but_stdout_is_redacted(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            package_path = temp_root / 'package.json'
            template_path = temp_root / 'template.json'
            patch_path = temp_root / 'patch.json'
            output_path = temp_root / 'ownership-injected-package.json'
            package_path.write_text(json.dumps(self._complete_package()), encoding='utf-8')
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')
            patch_path.write_text(json.dumps(self._valid_patch()), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'inject_annual_tax_ownership_patch_into_controlled_package',
                package=str(package_path),
                template=str(template_path),
                patch=str(patch_path),
                output=str(output_path),
                stdout=stdout,
            )

            summary = json.loads(stdout.getvalue())
            rendered_summary = json.dumps(summary, ensure_ascii=True)
            result = json.loads(output_path.read_text(encoding='utf-8'))
            self.assertTrue(summary['ownership_injected'])
            self.assertTrue(summary['ready_for_annual_generation'])
            self.assertTrue(result['package']['ownership']['participants'][0]['name'])
            self.assertNotIn('Socio Controlado Uno', rendered_summary)
            self.assertNotIn('11111111-1', rendered_summary)

    def test_command_refuses_versioned_patch_and_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            docs_dir = repo_root / 'docs'
            docs_dir.mkdir(parents=True)
            package_path = repo_root / 'package.json'
            template_path = repo_root / 'template.json'
            patch_path = docs_dir / 'ownership-patch.json'
            output_path = docs_dir / 'ownership-injected-package.json'
            package_path.write_text(json.dumps(self._complete_package()), encoding='utf-8')
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')
            patch_path.write_text(json.dumps(self._valid_patch()), encoding='utf-8')

            with override_settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'local-evidence'):
                    call_command(
                        'inject_annual_tax_ownership_patch_into_controlled_package',
                        package=str(package_path),
                        template=str(template_path),
                        patch=str(patch_path),
                        output=str(output_path),
                        stdout=StringIO(),
                    )

    def test_command_missing_patch_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            package_path = temp_root / 'package.json'
            template_path = temp_root / 'template.json'
            patch_path = temp_root / 'Socio Controlado Uno 11111111-1.json'
            output_path = temp_root / 'ownership-injected-package.json'
            package_path.write_text(json.dumps(self._complete_package()), encoding='utf-8')
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'inject_annual_tax_ownership_patch_into_controlled_package',
                    package=str(package_path),
                    template=str(template_path),
                    patch=str(patch_path),
                    output=str(output_path),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)

    def test_command_output_write_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            package_path = temp_root / 'package.json'
            template_path = temp_root / 'template.json'
            patch_path = temp_root / 'patch.json'
            output_path = temp_root / 'Socio Controlado Uno 11111111-1.json'
            output_path.mkdir()
            package_path.write_text(json.dumps(self._complete_package()), encoding='utf-8')
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')
            patch_path.write_text(json.dumps(self._valid_patch()), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'inject_annual_tax_ownership_patch_into_controlled_package',
                    package=str(package_path),
                    template=str(template_path),
                    patch=str(patch_path),
                    output=str(output_path),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
