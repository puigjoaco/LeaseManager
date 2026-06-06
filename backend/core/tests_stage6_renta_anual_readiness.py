import json
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from audit.models import AuditEvent
from contabilidad.models import (
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    ObligacionTributariaMensual,
)
from contabilidad.services import ensure_default_regime
from core.stage6_renta_anual_readiness import collect_stage6_renta_anual_readiness
from documentos.models import (
    DocumentoEmitido,
    EstadoDocumento,
    ExpedienteDocumental,
    OrigenDocumento,
    PlantillaDocumental,
    PoliticaFirmaYNotaria,
    TipoDocumental,
)
from patrimonio.models import Empresa, ParticipacionPatrimonial, Socio
from sii.models import (
    AmbienteSII,
    CapacidadSII,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    EstadoGateSII,
    F22PreparacionAnual,
    ProcesoRentaAnual,
)


VALID_DOCUMENT_SHA256 = 'd' * 64


class Stage6RentaAnualReadinessTests(TestCase):
    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='Empresa Stage6 SpA', rut='66666666-6'):
        socio_1 = self._create_socio(f'{nombre} Socio 1', f'{rut[:7]}1-1')
        socio_2 = self._create_socio(f'{nombre} Socio 2', f'{rut[:7]}2-2')
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_1,
            empresa_owner=empresa,
            porcentaje='60.00',
            vigente_desde=date(2025, 1, 1),
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_2,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde=date(2025, 1, 1),
            activo=True,
        )
        return empresa

    def _sii_readiness_fields(self, prefix):
        return {
            'certificado_ref': f'certificado-{prefix}-ref',
            'evidencia_ref': f'evidencia-{prefix}-gate',
            'prueba_flujo_ref': f'prueba-{prefix}-flujo',
            'autorizacion_ambiente_ref': f'ambiente-{prefix}-certificacion',
            'regla_fiscal_ref': f'regla-{prefix}-validada',
        }

    def _activate_fiscal_config(self, empresa):
        return ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=ensure_default_regime(),
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            tasa_ppm_vigente='10.00',
            aplica_ppm=True,
            ddjj_habilitadas=['1887'],
            inicio_ejercicio=date(2025, 1, 1),
            moneda_funcional='CLP',
            estado='activa',
        )

    def _open_capability(self, empresa, capability_key, prefix=None, **overrides):
        payload = {
            'empresa': empresa,
            'capacidad_key': capability_key,
            **self._sii_readiness_fields(prefix or capability_key.lower()),
            'ambiente': AmbienteSII.CERTIFICATION,
            'estado_gate': EstadoGateSII.OPEN,
            'ultimo_resultado': {},
        }
        payload.update(overrides)
        return CapacidadTributariaSII.objects.create(**payload)

    def _create_twelve_approved_closes(self, empresa, fiscal_year=2025):
        for month in range(1, 13):
            CierreMensualContable.objects.create(
                empresa=empresa,
                anio=fiscal_year,
                mes=month,
                estado=EstadoCierreMensual.APPROVED,
                fecha_preparacion=timezone.now(),
                fecha_aprobacion=timezone.now(),
                resumen_obligaciones={'month': month, 'source': 'stage6-controlled'},
            )
            ObligacionTributariaMensual.objects.create(
                empresa=empresa,
                anio=fiscal_year,
                mes=month,
                obligacion_tipo='PPM',
                base_imponible=Decimal('100000.00'),
                monto_calculado=Decimal('10000.00'),
                estado_preparacion=EstadoPreparacionTributaria.APPROVED,
                detalle_calculo={'source': 'stage6-controlled'},
            )

    def _annual_summary(self, fiscal_year=2025):
        return {
            'fiscal_year': fiscal_year,
            'obligaciones': [
                {
                    'anio': fiscal_year,
                    'mes': month,
                    'tipo': 'PPM',
                    'monto_calculado': '10000.00',
                    'estado_preparacion': EstadoPreparacionTributaria.APPROVED,
                }
                for month in range(1, 13)
            ],
            'total_obligaciones': 12,
            'total_monto_calculado': '120000.00',
        }

    def _create_tax_support_document(self, process):
        PoliticaFirmaYNotaria.objects.get_or_create(
            tipo_documental=TipoDocumental.TAX_SUPPORT,
            defaults={
                'requiere_firma_arrendador': False,
                'requiere_firma_arrendatario': False,
                'requiere_codeudor': False,
                'requiere_notaria': False,
                'modo_firma_permitido': 'firma_simple',
                'estado': 'activa',
            },
        )
        PlantillaDocumental.objects.get_or_create(
            tipo_documental=TipoDocumental.TAX_SUPPORT,
            version_plantilla='stage6-v1',
            defaults={
                'plantilla_ref': 'templates/respaldo_tributario/stage6-v1',
                'checksum_plantilla': VALID_DOCUMENT_SHA256,
                'descripcion': 'Plantilla controlada para respaldo tributario anual.',
                'estado': 'activa',
            },
        )
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='proceso_renta_anual',
            entidad_id=str(process.pk),
            owner_operativo='tributario-stage6',
        )
        user = get_user_model().objects.create_user(
            username=f'stage6-docs-{process.pk}',
            password='secret123',
        )
        return DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.TAX_SUPPORT,
            version_plantilla='stage6-v1',
            checksum=VALID_DOCUMENT_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen=OrigenDocumento.GENERATED,
            estado=EstadoDocumento.ISSUED,
            storage_ref='local-evidence/stage6/certificado-renta-anual.pdf',
        )

    def _create_valid_local_matrix(self):
        empresa = self._create_active_empresa()
        self._activate_fiscal_config(empresa)
        ddjj_capability = self._open_capability(empresa, CapacidadSII.DDJJ_PREPARACION, 'ddjj')
        f22_capability = self._open_capability(empresa, CapacidadSII.F22_PREPARACION, 'f22')
        self._create_twelve_approved_closes(empresa)
        summary = self._annual_summary()
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.APPROVED,
            fecha_preparacion=timezone.now(),
            resumen_anual=summary,
            paquete_ddjj_ref='ddjj-package-stage6-controlled',
            borrador_f22_ref='f22-draft-stage6-controlled',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2026,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': summary},
            paquete_ref='ddjj-package-stage6-controlled',
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2026,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_f22={'resumen_anual': summary, 'regimen_tributario': 'propyme-general-v1'},
            borrador_ref='f22-draft-stage6-controlled',
        )
        self._create_tax_support_document(process)
        return empresa

    def _collect_with_final_refs(self):
        return collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='annual-tax-rule-expert-v1',
            certificates_proof_ref='annual-certificates-controlled-v1',
            responsible_ref='stage6-responsibles-v1',
            source_label='stage6-controlled-v1',
            authorization_ref='stage6-authorization-v1',
            source_kind='snapshot_controlado',
        )

    def test_empty_database_reports_partial_without_sensitive_values(self):
        result = collect_stage6_renta_anual_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage6.source_kind_not_authorized', issue_codes)
        self.assertIn('stage6.fiscal_config_missing', issue_codes)
        self.assertIn('stage6.ddjj.open_capability_missing', issue_codes)
        self.assertIn('stage6.annual_process_missing', issue_codes)
        self.assertIn('stage6.tax_support_document_missing', issue_codes)
        self.assertIn('stage6.fiscal_rule_ref_missing', issue_codes)
        self.assertNotIn('://', json.dumps(result))

    def test_annual_status_updated_event_without_transition_metadata_is_blocking(self):
        AuditEvent.objects.create(
            event_type='sii.ddjj_preparacion.status_updated',
            entity_type='ddjj_preparacion',
            entity_id='1',
            summary='Actualizacion anual heredada sin metadata de transicion.',
            metadata={'estado_nuevo': EstadoPreparacionTributaria.APPROVED},
        )

        result = collect_stage6_renta_anual_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertIn('stage6.audit.annual_status_transition_metadata_missing', issue_codes)
        self.assertEqual(result['sections']['audit']['annual_status_transition_metadata_missing'], 1)

    def test_valid_authorized_matrix_and_non_sensitive_refs_can_pass_readiness(self):
        self._create_valid_local_matrix()

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage6_renta_anual'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertTrue(result['sections']['source_trace']['source_label'])
        self.assertTrue(result['sections']['source_trace']['authorization_ref'])
        self.assertEqual(result['issues'], [])

    def test_valid_local_matrix_and_non_sensitive_refs_cannot_close_readiness(self):
        self._create_valid_local_matrix()

        result = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='annual-tax-rule-expert-v1',
            certificates_proof_ref='annual-certificates-controlled-v1',
            responsible_ref='stage6-responsibles-v1',
            source_kind='local',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage6.source_kind_not_authorized', issue_codes)

    def test_authorized_source_requires_source_trace_refs(self):
        self._create_valid_local_matrix()

        result = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='annual-tax-rule-expert-v1',
            certificates_proof_ref='annual-certificates-controlled-v1',
            responsible_ref='stage6-responsibles-v1',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertIn('stage6.source_label_missing', issue_codes)
        self.assertIn('stage6.authorization_ref_missing', issue_codes)
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_authorized_source_sensitive_trace_refs_are_classified(self):
        self._create_valid_local_matrix()

        result = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='annual-tax-rule-expert-v1',
            certificates_proof_ref='annual-certificates-controlled-v1',
            responsible_ref='stage6-responsibles-v1',
            source_kind='snapshot_controlado',
            source_label='https://example.test/stage6?signed_token=secret',
            authorization_ref='Bearer stage6-secret-token',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertIn('stage6.source_label_sensitive', issue_codes)
        self.assertIn('stage6.authorization_ref_sensitive', issue_codes)
        self.assertNotIn('stage6.source_label_missing', issue_codes)
        self.assertNotIn('stage6.authorization_ref_missing', issue_codes)
        self.assertTrue(result['sections']['source_trace_sensitive']['source_label'])
        self.assertTrue(result['sections']['source_trace_sensitive']['authorization_ref'])
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_authorized_source_sensitive_final_refs_are_classified(self):
        self._create_valid_local_matrix()

        result = collect_stage6_renta_anual_readiness(
            source_kind='snapshot_controlado',
            source_label='stage6-controlled-source-v1',
            authorization_ref='stage6-authorization-v1',
            stage5_evidence_ref='https://example.test/stage5?signed_token=secret',
            stage4_sii_evidence_ref='https://example.test/stage4?signed_token=secret',
            fiscal_rule_ref='https://example.test/fiscal-rule?signed_token=secret',
            certificates_proof_ref='https://example.test/certificates?signed_token=secret',
            responsible_ref='Bearer stage6-responsible-secret',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        expected_sensitive_codes = {
            'stage6.stage5_evidence_ref_sensitive',
            'stage6.stage4_sii_evidence_ref_sensitive',
            'stage6.fiscal_rule_ref_sensitive',
            'stage6.certificates_proof_ref_sensitive',
            'stage6.responsible_ref_sensitive',
        }
        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertTrue(expected_sensitive_codes.issubset(issue_codes))
        self.assertNotIn('stage6.stage5_evidence_ref_missing', issue_codes)
        self.assertNotIn('stage6.stage4_sii_evidence_ref_missing', issue_codes)
        self.assertNotIn('stage6.fiscal_rule_ref_missing', issue_codes)
        self.assertNotIn('stage6.certificates_proof_ref_missing', issue_codes)
        self.assertNotIn('stage6.responsible_ref_missing', issue_codes)
        for key in (
            'stage5_evidence_ref',
            'stage4_sii_evidence_ref',
            'fiscal_rule_ref',
            'certificates_proof_ref',
            'responsible_ref',
        ):
            self.assertTrue(result['sections']['final_evidence_sensitive'][key])
            self.assertFalse(result['sections']['final_evidence'][key])

    def test_process_without_twelve_approved_closes_is_blocking(self):
        self._create_valid_local_matrix()
        CierreMensualContable.objects.filter(mes=12).update(estado=EstadoCierreMensual.PREPARED)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_twelve_closes_missing', issue_codes)

    def test_open_annual_capability_without_readiness_refs_is_blocking(self):
        empresa = self._create_active_empresa(nombre='AnnualCapabilityCo', rut='67676767-6')
        self._activate_fiscal_config(empresa)
        CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key=CapacidadSII.DDJJ_PREPARACION,
            certificado_ref='cert-stage6',
            ambiente=AmbienteSII.CERTIFICATION,
            estado_gate=EstadoGateSII.OPEN,
        )

        result = collect_stage6_renta_anual_readiness()

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.annual_capability_invalid', {issue['code'] for issue in result['issues']})

    def test_annual_capabilities_process_ddjj_and_f22_require_same_company_fiscal_config(self):
        empresa_con_config = self._create_active_empresa(nombre='FiscalConfiguredStage6Co', rut='65656565-6')
        self._activate_fiscal_config(empresa_con_config)
        empresa_sin_config = self._create_active_empresa(nombre='AnnualNoFiscalCo', rut='75757575-7')
        ddjj_capability = self._open_capability(
            empresa_sin_config,
            CapacidadSII.DDJJ_PREPARACION,
            'ddjj-no-fiscal',
        )
        f22_capability = self._open_capability(
            empresa_sin_config,
            CapacidadSII.F22_PREPARACION,
            'f22-no-fiscal',
        )
        self._create_twelve_approved_closes(empresa_sin_config)
        summary = self._annual_summary()
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa_sin_config,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.APPROVED,
            fecha_preparacion=timezone.now(),
            resumen_anual=summary,
            paquete_ddjj_ref='ddjj-package-stage6-no-fiscal',
            borrador_f22_ref='f22-draft-stage6-no-fiscal',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa_sin_config,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2026,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': summary},
            paquete_ref='ddjj-package-stage6-no-fiscal',
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa_sin_config,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2026,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_f22={'resumen_anual': summary, 'regimen_tributario': 'propyme-general-v1'},
            borrador_ref='f22-draft-stage6-no-fiscal',
        )
        self._create_tax_support_document(process)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.annual_capability_fiscal_config_missing', issue_codes)
        self.assertIn('stage6.annual_process_fiscal_config_missing', issue_codes)
        self.assertIn('stage6.ddjj_fiscal_config_missing', issue_codes)
        self.assertIn('stage6.f22_fiscal_config_missing', issue_codes)
        self.assertEqual(result['sections']['annual_capabilities']['open_without_active_fiscal_config'], 2)
        self.assertEqual(result['sections']['annual_process']['without_active_fiscal_config'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_without_active_fiscal_config'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_without_active_fiscal_config'], 1)

    def test_process_without_summary_or_annual_documents_is_blocking(self):
        empresa = self._create_active_empresa(nombre='ProcessNoDocsCo', rut='68686868-6')
        self._activate_fiscal_config(empresa)
        self._open_capability(empresa, CapacidadSII.DDJJ_PREPARACION, 'ddjj-no-docs')
        self._open_capability(empresa, CapacidadSII.F22_PREPARACION, 'f22-no-docs')
        self._create_twelve_approved_closes(empresa)
        ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.PREPARED,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.annual_process_summary_missing', issue_codes)
        self.assertIn('stage6.ddjj_missing_for_process', issue_codes)
        self.assertIn('stage6.f22_missing_for_process', issue_codes)

    def test_annual_payloads_with_wrong_fiscal_year_are_blocking(self):
        self._create_valid_local_matrix()
        wrong_summary = self._annual_summary(fiscal_year=2024)
        ProcesoRentaAnual.objects.update(resumen_anual=wrong_summary)
        DDJJPreparacionAnual.objects.update(
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': wrong_summary}
        )
        F22PreparacionAnual.objects.update(
            resumen_f22={'resumen_anual': wrong_summary, 'regimen_tributario': 'propyme-general-v1'}
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.annual_process_fiscal_year_mismatch', issue_codes)
        self.assertIn('stage6.ddjj_summary_fiscal_year_mismatch', issue_codes)
        self.assertIn('stage6.f22_summary_fiscal_year_mismatch', issue_codes)

    def test_sensitive_annual_payload_keys_are_blocking(self):
        self._create_valid_local_matrix()
        summary = self._annual_summary()
        ProcesoRentaAnual.objects.update(resumen_anual={**summary, 'api_key': None})
        DDJJPreparacionAnual.objects.update(
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': summary, 'access_token': None}
        )
        F22PreparacionAnual.objects.update(
            resumen_f22={'resumen_anual': summary, 'regimen_tributario': 'propyme-general-v1', 'credential': None}
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.annual_process_sensitive_payload', issue_codes)
        self.assertIn('stage6.ddjj_sensitive_payload', issue_codes)
        self.assertIn('stage6.f22_sensitive_payload', issue_codes)
        self.assertEqual(result['sections']['annual_process']['process_sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_sensitive_payload'], 1)
        self.assertNotIn('api_key', json.dumps(result))

    def test_ddjj_and_f22_approved_without_refs_or_presented_are_blocking(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(paquete_ddjj_ref='', borrador_f22_ref='')
        DDJJPreparacionAnual.objects.update(paquete_ref='')
        F22PreparacionAnual.objects.update(borrador_ref='')

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_ddjj_ref_missing', issue_codes)
        self.assertIn('stage6.process_f22_ref_missing', issue_codes)
        self.assertIn('stage6.ddjj_ref_missing', issue_codes)
        self.assertIn('stage6.f22_ref_missing', issue_codes)

        DDJJPreparacionAnual.objects.update(estado_preparacion=EstadoPreparacionTributaria.PRESENTED, paquete_ref='ddjj-presented')
        F22PreparacionAnual.objects.update(estado_preparacion=EstadoPreparacionTributaria.PRESENTED, borrador_ref='f22-presented')
        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        self.assertIn('stage6.ddjj_presented_boundary', issue_codes)
        self.assertIn('stage6.f22_presented_boundary', issue_codes)

    def test_sensitive_annual_final_refs_are_classified_explicitly(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(
            paquete_ddjj_ref='https://sii.example.test/ddjj?token=secret',
            borrador_f22_ref='https://sii.example.test/f22?token=secret',
        )
        DDJJPreparacionAnual.objects.update(paquete_ref='https://sii.example.test/ddjj?token=secret')
        F22PreparacionAnual.objects.update(borrador_ref='https://sii.example.test/f22?token=secret')

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_ddjj_ref_sensitive', issue_codes)
        self.assertIn('stage6.process_f22_ref_sensitive', issue_codes)
        self.assertIn('stage6.ddjj_ref_sensitive', issue_codes)
        self.assertIn('stage6.f22_ref_sensitive', issue_codes)
        self.assertEqual(result['sections']['annual_process']['process_ddjj_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_process']['process_f22_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_ref_sensitive'], 1)
        self.assertNotIn('token=secret', json.dumps(result))

    def test_tax_support_document_must_be_valid_pdf(self):
        self._create_valid_local_matrix()
        DocumentoEmitido.objects.update(storage_ref='local-evidence/stage6/certificado.txt')

        result = self._collect_with_final_refs()

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_support_document_invalid', {issue['code'] for issue in result['issues']})

    def test_sensitive_final_refs_and_command_behaviour(self):
        self._create_valid_local_matrix()

        result = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='https://sii.example/rule',
            certificates_proof_ref='annual-certificates-controlled-v1',
            responsible_ref='stage6-responsibles-v1',
            source_label='stage6-controlled-v1',
            authorization_ref='stage6-authorization-v1',
            source_kind='snapshot_controlado',
        )
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        issue_codes = {issue['code'] for issue in result['issues']}
        self.assertIn('stage6.fiscal_rule_ref_sensitive', issue_codes)
        self.assertNotIn('stage6.fiscal_rule_ref_missing', issue_codes)
        self.assertTrue(result['sections']['final_evidence_sensitive']['fiscal_rule_ref'])

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'stage6_readiness.json'
            call_command('audit_stage6_renta_anual_readiness', output=str(output_path), stdout=StringIO())
            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage6.source_kind_not_authorized', {issue['code'] for issue in result['issues']})
        self.assertIn('annual_process', result['sections'])

        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage6-readiness-should-not-be-versioned.json'
        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_stage6_renta_anual_readiness',
                output=str(blocked_output),
                stdout=StringIO(),
            )
        self.assertFalse(blocked_output.exists())

        with self.assertRaises(CommandError):
            call_command('audit_stage6_renta_anual_readiness', fail_on_attention=True, stdout=StringIO())
