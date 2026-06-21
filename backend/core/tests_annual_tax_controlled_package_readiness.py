import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.annual_tax_controlled_db_load import CONTROLLED_DB_LOAD_SCHEMA_VERSION
from core.annual_tax_controlled_package_readiness import audit_annual_tax_controlled_package_readiness
from core.annual_tax_controlled_package_template import (
    CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION,
    build_annual_tax_controlled_db_load_template,
)
from core.annual_tax_source_manifest import build_annual_tax_source_manifest


class AnnualTaxControlledPackageReadinessTests(SimpleTestCase):
    def _write(self, root: Path, relative_path: str, content: str = 'controlled-test-source') -> None:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def _build_complete_source_tree(self, root: Path) -> None:
        for month in range(1, 13):
            self._write(
                root,
                f'Ano_2024/06_Respaldos_Tributarios/02_RCV_SII/01_Resumenes/2024-{month:02d}_RCV_Resumen_Compra_Registro.csv',
                'Tipo Documento;Monto Total\nFactura;1000\n',
            )
            self._write(
                root,
                f'Ano_2024/06_Respaldos_Tributarios/01_F29_y_Comprobantes/2024-{month:02d}_F29_Comprobante.pdf',
            )
            self._write(root, f'Ano_2024/02_Libro_Compra/{month:02d} Libro Compra 2024.pdf')
            self._write(root, f'Ano_2024/05_Remuneraciones/2024-{month:02d}_Liquidaciones_Resumen.pdf')

        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro Diario 2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro Mayor 2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Balance General 2024.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Renta Liquida.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Capital Propio.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Determinacion RAI.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Rentas Empresariales.pdf')
        self._write(root, 'Ano_2024/07_DDJJ_AT_2025/AT_2025_DJ_1887_Aceptada.pdf')
        self._write(root, 'Ano_2024/08_F22_Renta_AT_2025/AT_2025_Formulario_22_Compacto.pdf')

    def _manifest(self, source_root: Path) -> dict:
        return build_annual_tax_source_manifest(
            source_root=source_root,
            company_ref='inmobiliaria-puig',
            commercial_year=2024,
            tax_year=2025,
        )

    def _ownership_snapshot(self):
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

    def _ownership_review_handoff(self, *, ready=True):
        return {
            'schema_version': CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION,
            'source_checklist_hash': 'b' * 64,
            'reviewable_candidates_total': 10,
            'rendered_candidates_total': 10,
            'validation_present': ready,
            'participants_count': 2 if ready else 0,
            'percentage_total': '100.00' if ready else '0.00',
            'blocking_items_total': 0 if ready else 3,
            'blocking_item_keys': [] if ready else ['participants_completed_from_legal_review'],
            'validation_blockers': [] if ready else ['ownership_patch_validation_missing'],
            'ready_for_manual_review': True,
            'ready_for_controlled_db_load': ready,
            'can_inject_ownership_into_controlled_package': ready,
            'next_action': 'inject_validated_ownership_snapshot_into_package_ownership'
            if ready
            else 'complete_validated_ownership_patch_before_package_ownership',
            'writes_database': False,
            'stores_source_paths': False,
            'stores_person_names': False,
            'stores_rut_values': False,
            'auto_generates_ownership': False,
        }

    def _complete_package(self, *, f29_no_aplica_months=(), include_ownership=True):
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
                        'estado_preparacion': 'no_aplica',
                        'borrador_ref': '',
                        'resumen': {
                            'no_declaration': True,
                            'source': 'manifest.f29_no_declaration_months',
                        },
                    }
                    if month in f29_no_aplica_months
                    else {
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

    def test_template_draft_is_not_ready_until_manual_values_are_completed(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            template = build_annual_tax_controlled_db_load_template(manifest=self._manifest(source_root))

        result = audit_annual_tax_controlled_package_readiness(payload=template)

        self.assertFalse(result['ready_for_db_writer'])
        self.assertIn('monthly_value_placeholders', result['blockers'])
        self.assertIn('missing_control_refs', result['blockers'])
        self.assertIn('$.responsible_ref', result['missing_value_paths'])
        self.assertIn('$.months[0].ledger.libro_diario_ref', result['missing_value_paths'])
        self.assertIn('$.months[0].f29.borrador_ref', result['missing_value_paths'])
        self.assertTrue(result['summary']['complete_12_months'])
        self.assertTrue(result['summary']['comparison_targets_present'])

    def test_complete_package_is_ready_for_db_writer_without_using_expected_outputs(self):
        result = audit_annual_tax_controlled_package_readiness(payload=self._complete_package())

        self.assertTrue(result['ready_for_db_writer'])
        self.assertTrue(result['ready_for_annual_generation'])
        self.assertFalse(result['ready_for_mirror_comparison'])
        self.assertEqual(result['blockers'], [])
        self.assertEqual(result['missing_value_paths'], [])
        self.assertFalse(result['safety']['uses_expected_outputs_as_inputs'])
        self.assertEqual(result['summary']['ownership_snapshot']['participants_count'], 2)
        self.assertFalse(result['summary']['labor_previsional_source']['required'])

    def test_labor_previsional_required_without_source_blocks_writer(self):
        package = self._complete_package()
        package['labor_previsional'] = {
            'required': True,
            'required_by_ddjj_forms': ['1887'],
            'source_ref': '',
            'source_refs': [{'path_ref': 'payroll-support-controlled'}],
            'monthly_support_months': list(range(1, 13)),
        }

        result = audit_annual_tax_controlled_package_readiness(payload=package)

        self.assertFalse(result['ready_for_db_writer'])
        self.assertIn('labor_previsional_source_missing', result['blockers'])
        self.assertIn('$.labor_previsional.source_ref', result['missing_value_paths'])
        self.assertTrue(result['summary']['labor_previsional_source']['required'])

    def test_labor_previsional_required_with_source_is_ready(self):
        package = self._complete_package()
        package['labor_previsional'] = {
            'required': True,
            'required_by_ddjj_forms': ['1887'],
            'source_ref': 'labor-previsional-ac2024-controlled',
            'source_refs': [{'path_ref': 'payroll-support-controlled'}],
            'monthly_support_months': list(range(1, 13)),
        }

        result = audit_annual_tax_controlled_package_readiness(payload=package)

        self.assertTrue(result['ready_for_db_writer'])
        self.assertEqual(result['blockers'], [])
        self.assertTrue(result['summary']['labor_previsional_source']['source_ref_present'])

    def test_complete_monthly_package_without_ownership_is_not_ready_for_annual_generation(self):
        result = audit_annual_tax_controlled_package_readiness(
            payload=self._complete_package(include_ownership=False),
        )

        self.assertTrue(result['ready_for_db_writer'])
        self.assertFalse(result['ready_for_annual_generation'])
        self.assertFalse(result['ready_for_mirror_comparison'])
        self.assertEqual(result['blockers'], [])
        self.assertIn('ownership_snapshot_missing', result['annual_generation_blockers'])
        self.assertIn('$.ownership', result['annual_generation_missing_paths'])
        self.assertFalse(result['summary']['ownership_snapshot']['present'])
        self.assertFalse(result['summary']['ownership_review_handoff']['present'])

    def test_ownership_review_handoff_does_not_replace_controlled_snapshot(self):
        package = self._complete_package(include_ownership=False)
        package['ownership_review'] = self._ownership_review_handoff(ready=True)

        result = audit_annual_tax_controlled_package_readiness(payload=package)

        self.assertTrue(result['ready_for_db_writer'])
        self.assertFalse(result['ready_for_annual_generation'])
        self.assertIn('ownership_snapshot_missing', result['annual_generation_blockers'])
        self.assertIn('ownership_review_ready_requires_package_ownership', result['warnings'])
        self.assertFalse(result['summary']['ownership_snapshot']['present'])
        self.assertTrue(result['summary']['ownership_review_handoff']['present'])
        self.assertTrue(result['summary']['ownership_review_handoff']['ready_for_controlled_db_load'])
        self.assertFalse(result['summary']['ownership_review_handoff']['replaces_ownership_snapshot'])

    def test_ownership_review_handoff_matches_controlled_snapshot(self):
        package = self._complete_package()
        package['ownership_review'] = self._ownership_review_handoff(ready=True)
        package['ownership_review']['redacted_patch_hash'] = 'c' * 64

        result = audit_annual_tax_controlled_package_readiness(payload=package)

        self.assertTrue(result['ready_for_db_writer'])
        self.assertTrue(result['ready_for_annual_generation'])
        self.assertNotIn('ownership_review_handoff_mismatch', result['annual_generation_blockers'])
        self.assertNotIn('ownership_review_redacted_patch_hash_missing', result['warnings'])
        self.assertTrue(result['summary']['ownership_review_handoff']['redacted_patch_hash_present'])

    def test_ownership_review_handoff_preserves_sanitized_readiness_sources(self):
        package = self._complete_package()
        package['ownership_review'] = self._ownership_review_handoff(ready=True)
        package['ownership_review']['redacted_patch_hash'] = 'c' * 64
        package['ownership_review']['question_source_summaries'] = [
            {
                'label': 'D:/Privado/Socio Controlado Uno 11111111-1/banco',
                'schema_version': 'company-bank-support-coverage-manifest.v1',
                'classification': 'blocking',
                'ready_flags': {
                    'ready_for_formal_bank_support_review': False,
                    'document_intake_ready_for_productive_review': False,
                    'document_intake_ready_for_formal_bank_support_manifest': True,
                    'D:/Privado/Socio Controlado Uno 11111111-1': True,
                },
                'issues_total': 2,
                'source_hash': 'd' * 64,
            }
        ]

        result = audit_annual_tax_controlled_package_readiness(payload=package)
        handoff = result['summary']['ownership_review_handoff']
        source_summary = handoff['question_source_summaries'][0]
        rendered_handoff = json.dumps(handoff, ensure_ascii=True)

        self.assertTrue(result['ready_for_annual_generation'])
        self.assertEqual(handoff['readiness_sources_total'], 1)
        self.assertEqual(source_summary['label'], 'source')
        self.assertFalse(source_summary['ready_flags']['ready_for_formal_bank_support_review'])
        self.assertFalse(source_summary['ready_flags']['document_intake_ready_for_productive_review'])
        self.assertTrue(source_summary['ready_flags']['document_intake_ready_for_formal_bank_support_manifest'])
        self.assertNotIn('D:/Privado/Socio Controlado Uno 11111111-1', source_summary['ready_flags'])
        self.assertNotIn('Socio Controlado Uno', rendered_handoff)
        self.assertNotIn('11111111-1', rendered_handoff)
        self.assertNotIn('D:/Privado', rendered_handoff)

    def test_ownership_review_handoff_mismatch_blocks_annual_generation(self):
        package = self._complete_package()
        package['ownership_review'] = self._ownership_review_handoff(ready=True)
        package['ownership_review']['redacted_patch_hash'] = 'c' * 64
        package['ownership_review']['participants_count'] = 1
        package['ownership_review']['percentage_total'] = '99.00'

        result = audit_annual_tax_controlled_package_readiness(payload=package)

        self.assertTrue(result['ready_for_db_writer'])
        self.assertFalse(result['ready_for_annual_generation'])
        self.assertIn('ownership_review_handoff_mismatch', result['annual_generation_blockers'])
        self.assertIn('ownership_review_participants_count_mismatch', result['warnings'])
        self.assertIn('ownership_review_percentage_total_mismatch', result['warnings'])
        self.assertIn('$.ownership_review.participants_count', result['annual_generation_invalid_paths'])
        self.assertIn('$.ownership_review.percentage_total', result['annual_generation_invalid_paths'])

    def test_invalid_ownership_snapshot_blocks_annual_generation_only(self):
        package = self._complete_package()
        package['ownership']['participants'][1]['percentage'] = '39.00'
        package['ownership']['participants'][1]['rut'] = '11.111.111-1'
        package['ownership']['participants'][1]['vigente_hasta'] = 'fecha-mala'

        result = audit_annual_tax_controlled_package_readiness(payload=package)

        self.assertTrue(result['ready_for_db_writer'])
        self.assertFalse(result['ready_for_annual_generation'])
        self.assertEqual(result['blockers'], [])
        self.assertIn('ownership_snapshot_invalid', result['annual_generation_blockers'])
        self.assertIn('$.ownership.participants', result['annual_generation_invalid_paths'])
        self.assertIn('$.ownership.participants[1].rut', result['annual_generation_invalid_paths'])
        self.assertIn('$.ownership.participants[1].vigente_hasta', result['annual_generation_invalid_paths'])

    def test_ownership_snapshot_must_use_year_end_date(self):
        package = self._complete_package()
        package['ownership']['as_of'] = '2024-06-30'

        result = audit_annual_tax_controlled_package_readiness(payload=package)

        self.assertTrue(result['ready_for_db_writer'])
        self.assertFalse(result['ready_for_annual_generation'])
        self.assertIn('ownership_snapshot_invalid', result['annual_generation_blockers'])
        self.assertIn('$.ownership.as_of', result['annual_generation_invalid_paths'])
        self.assertEqual(result['summary']['ownership_snapshot']['as_of'], '2024-06-30')
        self.assertEqual(result['summary']['ownership_snapshot']['required_as_of'], '2024-12-31')

    def test_ownership_participants_must_cover_year_end_snapshot_date(self):
        package = self._complete_package()
        package['ownership']['participants'][1]['vigente_hasta'] = '2024-09-30'

        result = audit_annual_tax_controlled_package_readiness(payload=package)

        self.assertTrue(result['ready_for_db_writer'])
        self.assertFalse(result['ready_for_annual_generation'])
        self.assertIn('ownership_snapshot_invalid', result['annual_generation_blockers'])
        self.assertIn('$.ownership.participants[1]', result['annual_generation_invalid_paths'])

    def test_no_declaration_f29_month_is_valid_without_borrador_ref(self):
        result = audit_annual_tax_controlled_package_readiness(
            payload=self._complete_package(f29_no_aplica_months={2, 12}),
        )

        self.assertTrue(result['ready_for_db_writer'])
        self.assertNotIn('$.months[1].f29.borrador_ref', result['missing_value_paths'])
        self.assertNotIn('f29_status_missing', result['blockers'])

    def test_expected_outputs_inside_package_block_readiness(self):
        package = self._complete_package()
        package['ddjj_expected_output'] = {'form': '1887'}

        result = audit_annual_tax_controlled_package_readiness(payload=package)

        self.assertFalse(result['ready_for_db_writer'])
        self.assertIn('expected_outputs_present', result['blockers'])
        self.assertIn('$.ddjj_expected_output', result['invalid_paths'])

    def test_command_outputs_readiness_and_refuses_versioned_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / 'package.json'
            package_path.write_text(json.dumps(self._complete_package()), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'audit_annual_tax_controlled_package_readiness',
                package=str(package_path),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            self.assertTrue(result['ready_for_db_writer'])

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'audit_annual_tax_controlled_package_readiness',
                    package=str(package_path),
                    output='docs/ac2024-controlled-package-readiness.json',
                    stdout=StringIO(),
                )

    def test_command_missing_package_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / 'Socio Controlado Uno 11111111-1.json'

            with self.assertRaises(CommandError) as error:
                call_command(
                    'audit_annual_tax_controlled_package_readiness',
                    package=str(missing_path),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No existe package JSON o no es un archivo legible.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)

    def test_command_read_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / 'Socio Controlado Uno 11111111-1.json'
            package_path.write_text(json.dumps(self._complete_package()), encoding='utf-8')

            with patch.object(
                Path,
                'read_text',
                side_effect=OSError('D:/Privado/Socio Controlado Uno 11111111-1/package.json'),
            ):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'audit_annual_tax_controlled_package_readiness',
                        package=str(package_path),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No se pudo leer package JSON.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)

    def test_command_write_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            package_path = temp_root / 'package.json'
            output_path = temp_root / 'Socio Controlado Uno 11111111-1' / 'readiness.json'
            package_path.write_text(json.dumps(self._complete_package()), encoding='utf-8')

            with patch.object(
                Path,
                'write_text',
                side_effect=OSError('D:/Privado/Socio Controlado Uno 11111111-1/readiness.json'),
            ):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'audit_annual_tax_controlled_package_readiness',
                        package=str(package_path),
                        output=str(output_path),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No se pudo escribir auditoria de paquete controlado.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)
