import json
import hashlib
import zipfile
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from audit.models import AuditEvent
from contabilidad.models import (
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    NaturalezaCuenta,
    ObligacionTributariaMensual,
    RegimenTributarioEmpresa,
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
from patrimonio.models import Propiedad, TipoInmueble
from sii.models import (
    AnnualEnterpriseRegisterMovement,
    AnnualEnterpriseRegisterSet,
    AnnualRealEstateItem,
    AnnualRealEstateSection,
    AnnualTaxArtifactMatrix,
    AnnualTaxArtifactMatrixItem,
    AnnualTaxDDJJFormLayout,
    AnnualTaxF22ExportLayout,
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxOfficialSource,
    AnnualTaxReviewChecklist,
    AmbienteSII,
    AnnualTaxSourceBundle,
    AnnualTaxTrialBalance,
    AnnualTaxTrialBalanceLine,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    CapacidadSII,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    DestinoMapeoTributarioAnual,
    EstadoAnnualEnterpriseRegister,
    EstadoAnnualTaxArtifactReview,
    EstadoAnnualTaxDDJJLayout,
    EstadoAnnualTaxF22ExportLayout,
    EstadoAnnualTaxOfficialSource,
    EstadoAnnualTaxReviewDecision,
    EstadoAnnualTaxSourceBundle,
    EstadoRegistro,
    EstadoReglaTributariaAnual,
    EstadoGateSII,
    F22PreparacionAnual,
    MedioAnnualTaxDDJJ,
    MedioAnnualTaxF22Export,
    MonthlyTaxFact,
    ProcesoRentaAnual,
    TaxCodeMapping,
    TaxYearRuleSet,
    TipoAnnualTaxOfficialSource,
)
from sii.services import (
    build_annual_tax_ddjj_ascii_export_candidate,
    build_annual_tax_ddjj_zip_export_candidate,
    build_annual_tax_export_file_package,
    build_annual_tax_f22_fixed_width_export_candidate,
    build_annual_tax_presentation_review_bundle,
    build_f22_fixed_width_entries_from_artifact_matrix,
    register_annual_tax_review_decision,
    summarize_annual_enterprise_registers,
    summarize_annual_real_estate_sections,
    summarize_annual_tax_artifact_matrices,
    summarize_annual_tax_dossiers,
    summarize_annual_tax_ddjj_layouts,
    summarize_annual_tax_f22_export_layouts,
    summarize_annual_tax_exports,
    summarize_annual_tax_review_checklists,
    summarize_annual_tax_trial_balances,
    summarize_annual_tax_workbooks,
    mark_annual_enterprise_register_warnings_reviewed,
    mark_annual_tax_artifact_matrix_warnings_reviewed,
    mark_annual_tax_workbook_warnings_reviewed,
    sync_annual_enterprise_registers,
    sync_annual_real_estate_section,
    sync_annual_tax_artifact_matrix,
    sync_annual_tax_dossier,
    sync_annual_tax_export,
    sync_annual_tax_review_checklist,
    sync_annual_tax_trial_balance,
    sync_annual_tax_workbooks,
    sync_monthly_tax_facts,
    verify_annual_tax_f22_fixed_width_export_candidate,
    verify_annual_tax_ddjj_ascii_export_candidate,
    verify_annual_tax_ddjj_zip_export_candidate,
    verify_annual_tax_export_file_package,
    verify_annual_tax_presentation_review_bundle,
    verify_annual_tax_controlled_presentation_package,
    verify_annual_tax_sii_certification_readiness_packet,
    write_annual_tax_ddjj_ascii_export_candidate,
    write_annual_tax_ddjj_zip_export_candidate,
    write_annual_tax_f22_fixed_width_export_candidate,
    write_annual_tax_export_file_package,
)


VALID_DOCUMENT_SHA256 = 'd' * 64


class Stage6RentaAnualReadinessTests(TestCase):
    def _f22_local_certification_kwargs(self):
        return {
            'certification_code_source_ref': 'sii-f22-at2026-cert-code-synthetic-local',
            'certification_responsible_review_ref': 'tax-reviewer-at2026-cert-code-controlled',
        }

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

    def _activate_unsupported_fiscal_config(self, empresa):
        regime = RegimenTributarioEmpresa.objects.create(
            codigo_regimen='RegimenManualNoAutomatizableV1',
            descripcion='Regimen manual no automatizable en v1',
            estado='activa',
        )
        return ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=regime,
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

    def _create_official_source(self, *, anio_tributario=2026, applies_to='', regime_code=''):
        target_key = applies_to.lower() if applies_to else 'ruleset'
        return AnnualTaxOfficialSource.objects.create(
            anio_tributario=anio_tributario,
            source_key=f'expert-{target_key}-at{anio_tributario}',
            source_type=TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
            title=f'Revision experta {target_key} AT{anio_tributario}',
            source_ref=f'expert-{target_key}-source-ref-at{anio_tributario}',
            source_hash='f' * 64,
            retrieved_on=date(2026, 6, 14),
            responsible_ref='tax-source-reviewer-controlled',
            estado=EstadoAnnualTaxOfficialSource.APPROVED,
            applies_to=applies_to,
            regime_code=regime_code,
            scope_note='Fuente experta controlada para pruebas locales Stage 6.',
            metadata={'source': 'stage6-controlled'},
        )

    def _create_real_estate_contribution_source(self, *, anio_tributario=2026, regime_code=''):
        return AnnualTaxOfficialSource.objects.create(
            anio_tributario=anio_tributario,
            source_key=f'expert-real-estate-contributions-at{anio_tributario}',
            source_type=TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
            title=f'Revision experta contribuciones bienes raices AT{anio_tributario}',
            source_ref=f'expert-real-estate-contributions-source-ref-at{anio_tributario}',
            source_hash='9' * 64,
            retrieved_on=date(2026, 6, 14),
            responsible_ref='real-estate-tax-reviewer-controlled',
            estado=EstadoAnnualTaxOfficialSource.APPROVED,
            applies_to=DestinoMapeoTributarioAnual.F22,
            regime_code=regime_code,
            scope_note='Fuente experta controlada para contribuciones y codigos F22 de bienes raices.',
            metadata={'source': 'stage6-controlled', 'real_estate_contributions': True},
        )

    def _create_f22_export_format_source(self, *, anio_tributario=2026, regime_code=''):
        return AnnualTaxOfficialSource.objects.create(
            anio_tributario=anio_tributario,
            source_key=f'expert-f22-export-format-at{anio_tributario}',
            source_type=TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
            title=f'Revision experta formato export F22 AT{anio_tributario}',
            source_ref=f'expert-f22-export-format-source-ref-at{anio_tributario}',
            source_hash='8' * 64,
            retrieved_on=date(2026, 6, 14),
            responsible_ref='f22-export-format-reviewer-controlled',
            estado=EstadoAnnualTaxOfficialSource.APPROVED,
            applies_to=DestinoMapeoTributarioAnual.F22,
            form_code='F22',
            regime_code=regime_code,
            scope_note='Fuente experta controlada para formato/certificacion F22 local.',
            metadata={'source': 'stage6-controlled', 'f22_export_format': True, 'official_format': False},
        )

    def _create_ddjj_layouts(self, config, *, anio_tributario=2026):
        source = self._create_official_source(
            anio_tributario=anio_tributario,
            applies_to=DestinoMapeoTributarioAnual.DDJJ,
            regime_code=config.regimen_tributario.codigo_regimen,
        )
        layouts = []
        for form_code in config.ddjj_habilitadas:
            layout = AnnualTaxDDJJFormLayout(
                anio_tributario=anio_tributario,
                form_code=str(form_code),
                title=f'DDJJ {form_code} controlada',
                periodicidad='Anual',
                allows_electronic_form=True,
                allows_file_importer=True,
                allows_file_upload=False,
                allows_commercial_software=True,
                allows_assistant=False,
                medio_preferente=MedioAnnualTaxDDJJ.COMMERCIAL_SOFTWARE,
                due_date_label=f'AT{anio_tributario}-plazo-ddjj-{form_code}',
                certificate_code=f'cert-ddjj-{form_code}',
                certificate_due_label=f'AT{anio_tributario}-plazo-certificado-{form_code}',
                resolution_ref=f'resolution-ddjj-{form_code}-controlled',
                declaration_status='preparacion_local_revisable',
                layout_ref=f'layout-ddjj-{form_code}-controlled',
                instructions_ref=f'instructions-ddjj-{form_code}-controlled',
                responsible_ref='stage6-ddjj-layout-owner',
                official_media_source=source,
                official_form_source=source,
                warnings=[],
                source_payload={
                    'source': 'stage6-controlled',
                    'anio_tributario': anio_tributario,
                    'form_code': str(form_code),
                    'record_format_kind': 'ascii_fixed_width_positional',
                    'ddjj_ascii_record_length': 24,
                    'ddjj_ascii_general_instructions_ref': 'sii-ddjj-at2026-general-ascii',
                    'ddjj_ascii_layout_review_ref': f'ddjj-{form_code}-ascii-layout-reviewed',
                    'official_format': False,
                    'sii_submission': False,
                },
                estado=EstadoAnnualTaxDDJJLayout.PREPARED,
            )
            layout.hash_layout = layout.compute_hash_layout()
            layout.full_clean()
            layout.save()
            layouts.append(layout)
        return layouts

    def _create_f22_export_layout(self, config, *, anio_tributario=2026, warnings=None):
        certification_source = self._create_official_source(
            anio_tributario=anio_tributario,
            applies_to=DestinoMapeoTributarioAnual.F22,
            regime_code=config.regimen_tributario.codigo_regimen,
        )
        AnnualTaxOfficialSource.objects.filter(pk=certification_source.pk).update(
            metadata={'source': 'stage6-controlled', 'f22_export_format': True}
        )
        certification_source.refresh_from_db()
        instructions_source = certification_source
        layout = AnnualTaxF22ExportLayout(
            anio_tributario=anio_tributario,
            form_code='F22',
            title=f'F22 AT{anio_tributario} preview local controlado',
            allows_local_preview=True,
            allows_certified_file=False,
            allows_supervised_portal=False,
            medio_preferente=MedioAnnualTaxF22Export.LOCAL_PREVIEW,
            certification_ref=f'f22-certification-at{anio_tributario}-controlled',
            format_ref=f'f22-layout-at{anio_tributario}-controlled',
            instructions_ref=f'f22-instructions-at{anio_tributario}-controlled',
            responsible_ref='stage6-f22-layout-owner',
            official_certification_source=certification_source,
            official_instructions_source=instructions_source,
            warnings=list(warnings or []),
            source_payload={
                'source': 'stage6-controlled',
                'anio_tributario': anio_tributario,
                'form_code': 'F22',
                'official_format': False,
                'sii_submission': False,
                'final_tax_calculation': False,
            },
            estado=EstadoAnnualTaxF22ExportLayout.PREPARED,
        )
        layout.hash_layout = layout.compute_hash_layout()
        layout.full_clean()
        layout.save()
        return layout

    def _create_approved_tax_year_ruleset(self, config, anio_tributario=2026):
        rule_source = self._create_official_source(
            anio_tributario=anio_tributario,
            regime_code=config.regimen_tributario.codigo_regimen,
        )
        rule_set = TaxYearRuleSet.objects.create(
            anio_tributario=anio_tributario,
            regimen_tributario=config.regimen_tributario,
            version='AT2026-controlled-v1',
            estado=EstadoReglaTributariaAnual.APPROVED,
            fuente_ref='tax-rule-source-at2026-controlled',
            hash_normativo='a' * 64,
            responsable_aprobacion_ref='tax-rule-reviewer-controlled',
            official_source=rule_source,
            metadata={'source': 'stage6-controlled'},
        )
        for destino, codigo_interno, codigo_destino, source_metric in (
            (
                DestinoMapeoTributarioAnual.RLI,
                'lease.revenue.net',
                'RLI-ING-001',
                'monthly_tax_facts.rent_distributions_total_devengado',
            ),
            (
                DestinoMapeoTributarioAnual.CPT,
                'lease.capital.taxable',
                'CPT-CAP-001',
                'monthly_tax_facts.obligations_total_amount',
            ),
            (
                DestinoMapeoTributarioAnual.RAI,
                'lease.register.rai',
                'RAI-REG-001',
                '',
            ),
            (
                DestinoMapeoTributarioAnual.SAC,
                'lease.register.sac',
                'SAC-REG-001',
                '',
            ),
        ):
            metadata = {'source': 'stage6-controlled'}
            if source_metric:
                metadata['source_metric'] = source_metric
            mapping_source = self._create_official_source(
                anio_tributario=anio_tributario,
                applies_to=destino,
                regime_code=config.regimen_tributario.codigo_regimen,
            )
            TaxCodeMapping.objects.create(
                rule_set=rule_set,
                destino=destino,
                codigo_interno=codigo_interno,
                codigo_destino=codigo_destino,
                formula_ref=f'formula-ref-{codigo_destino.lower()}-controlled',
                evidencia_ref=f'evidence-ref-{codigo_destino.lower()}-controlled',
                official_source=mapping_source,
                metadata=metadata,
            )
        return rule_set

    def _create_annual_source_bundle(
        self,
        empresa,
        *,
        anio_tributario=2026,
        fiscal_year=2025,
        real_estate_contribution_source=None,
        real_estate_contributions_by_property_id=None,
        f22_export_format_source=None,
    ):
        source_summary = {
            'empresa_id': empresa.id,
            'anio_comercial': fiscal_year,
            'approved_close_months': list(range(1, 13)),
            'approved_closes_total': 12,
            'obligation_months': list(range(1, 13)),
            'obligations_total': 12,
            'obligations_total_amount': '120000.00',
            'f29_preparations_total': 0,
            'source_scope': 'stage6-controlled',
            'real_estate_contribuciones': {
                'source': 'official_or_expert_review' if real_estate_contribution_source else 'not_loaded_v1',
                'official_source_id': real_estate_contribution_source.id if real_estate_contribution_source else None,
                'values_by_property_id': real_estate_contributions_by_property_id or {},
                'final_tax_calculation': False,
            },
            'f22_export_format': {
                'source': 'official_or_expert_review' if f22_export_format_source else 'not_loaded_v1',
                'official_source_id': f22_export_format_source.id if f22_export_format_source else None,
                'official_format': False,
                'sii_submission': False,
                'final_tax_calculation': False,
                'requires_official_format_gate': True,
                'requires_explicit_submission_authorization': True,
            },
        }
        source_hash = hashlib.sha256(
            json.dumps(source_summary, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)
            .encode('utf-8')
        ).hexdigest()
        return AnnualTaxSourceBundle.objects.create(
            empresa=empresa,
            anio_tributario=anio_tributario,
            anio_comercial=fiscal_year,
            source_kind='snapshot_controlado',
            source_label='stage6-controlled-v1',
            authorization_ref='stage6-authorization-v1',
            responsible_ref='stage6-source-owner-v1',
            hash_fuentes=source_hash,
            resumen_fuentes=source_summary,
            estado=EstadoAnnualTaxSourceBundle.FROZEN,
        )

    def _create_annual_trial_balance_source(self, empresa, fiscal_year=2025):
        revenue_account, _ = CuentaContable.objects.get_or_create(
            empresa=empresa,
            plan_cuentas_version='stage6-controlled',
            codigo='4100',
            defaults={
                'nombre': 'Ingresos por arriendo',
                'naturaleza': NaturalezaCuenta.CREDIT,
                'nivel': 1,
                'estado': 'activa',
            },
        )
        asset_account, _ = CuentaContable.objects.get_or_create(
            empresa=empresa,
            plan_cuentas_version='stage6-controlled',
            codigo='1100',
            defaults={
                'nombre': 'Banco recaudador',
                'naturaleza': NaturalezaCuenta.DEBIT,
                'nivel': 1,
                'estado': 'activa',
            },
        )
        return BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo=f'{fiscal_year}-12',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            storage_ref=f'balance-comprobacion-stage6-{empresa.id}-{fiscal_year}',
            resumen={
                'source': 'stage6-controlled',
                'lineas_balance_8_columnas': [
                    {
                        'codigo_cuenta': revenue_account.codigo,
                        'clasificador_dj1847': 'RLI-LEASE-REVENUE',
                        'sumas_haber_clp': '1200000.00',
                        'saldo_acreedor_clp': '1200000.00',
                        'resultado_ganancia_clp': '1200000.00',
                        'formula_ref': 'dj1847-rli-revenue-controlled',
                        'evidencia_ref': 'balance-eight-columns-revenue-controlled',
                    },
                    {
                        'codigo_cuenta': asset_account.codigo,
                        'clasificador_dj1847': 'CPT-CASH-ASSET',
                        'sumas_debe_clp': '1200000.00',
                        'saldo_deudor_clp': '1200000.00',
                        'inventario_activo_clp': '1200000.00',
                        'formula_ref': 'dj1847-cpt-cash-controlled',
                        'evidencia_ref': 'balance-eight-columns-cash-controlled',
                    },
                ],
            },
        )

    def _create_valid_local_matrix(self):
        empresa = self._create_active_empresa()
        config = self._activate_fiscal_config(empresa)
        rule_set = self._create_approved_tax_year_ruleset(config)
        ddjj_capability = self._open_capability(empresa, CapacidadSII.DDJJ_PREPARACION, 'ddjj')
        f22_capability = self._open_capability(empresa, CapacidadSII.F22_PREPARACION, 'f22')
        self._create_twelve_approved_closes(empresa)
        propiedad = Propiedad.objects.create(
            rol_avaluo='ROL-STAGE6-001',
            direccion='Propiedad Stage 6',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.APARTMENT,
            codigo_propiedad='STG6-001',
            estado='activa',
            empresa_owner=empresa,
        )
        real_estate_source = self._create_real_estate_contribution_source(
            regime_code=config.regimen_tributario.codigo_regimen,
        )
        f22_export_format_source = self._create_f22_export_format_source(
            regime_code=config.regimen_tributario.codigo_regimen,
        )
        source_bundle = self._create_annual_source_bundle(
            empresa,
            real_estate_contribution_source=real_estate_source,
            real_estate_contributions_by_property_id={
                str(propiedad.id): {
                    'contribuciones_clp': '345000.00',
                    'codigo_f22': 'F22-BIENES-RAICES',
                    'evidencia_ref': 'real-estate-contributions-controlled',
                },
            },
            f22_export_format_source=f22_export_format_source,
        )
        monthly_facts = sync_monthly_tax_facts(empresa, 2025)
        self._create_annual_trial_balance_source(empresa, 2025)
        summary = self._annual_summary()
        summary['annual_tax_source_bundle'] = {
            'id': source_bundle.id,
            'source_kind': source_bundle.source_kind,
            'source_label': source_bundle.source_label,
            'hash_fuentes': source_bundle.hash_fuentes,
            'anio_comercial': source_bundle.anio_comercial,
            'approved_closes_total': source_bundle.resumen_fuentes['approved_closes_total'],
            'obligations_total': source_bundle.resumen_fuentes['obligations_total'],
            'f29_preparations_total': source_bundle.resumen_fuentes['f29_preparations_total'],
        }
        summary['annual_tax_monthly_facts'] = {
            'total': len(monthly_facts),
            'months': sorted(fact.mes for fact in monthly_facts),
            'obligations_total': sum(
                int((fact.resumen_hecho or {}).get('obligations_total') or 0)
                for fact in monthly_facts
            ),
            'rent_distributions_total': sum(
                int((fact.resumen_hecho or {}).get('rent_distributions_total') or 0)
                for fact in monthly_facts
            ),
            'liquidation_lines_total': sum(
                int((fact.resumen_hecho or {}).get('liquidation_lines_total') or 0)
                for fact in monthly_facts
            ),
        }
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.APPROVED,
            source_bundle=source_bundle,
            fecha_preparacion=timezone.now(),
            resumen_anual=summary,
            paquete_ddjj_ref='ddjj-package-stage6-controlled',
            borrador_f22_ref='f22-draft-stage6-controlled',
            responsable_revision_ref='stage6-review-owner-controlled',
        )
        sync_annual_tax_trial_balance(process, rule_set, source_bundle)
        sync_annual_tax_workbooks(process, rule_set, source_bundle)
        sync_annual_enterprise_registers(process, rule_set, source_bundle)
        sync_annual_real_estate_section(process, rule_set, source_bundle)
        self._create_ddjj_layouts(config)
        self._create_f22_export_layout(config)
        summary['annual_tax_trial_balances'] = summarize_annual_tax_trial_balances(process)
        summary['annual_tax_workbooks'] = summarize_annual_tax_workbooks(process)
        summary['annual_enterprise_registers'] = summarize_annual_enterprise_registers(process)
        summary['annual_real_estate_sections'] = summarize_annual_real_estate_sections(process)
        summary['annual_tax_ddjj_layouts'] = summarize_annual_tax_ddjj_layouts(process)
        summary['annual_tax_f22_export_layouts'] = summarize_annual_tax_f22_export_layouts(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_artifact_matrix(process, rule_set, source_bundle, config)
        summary['annual_tax_artifact_matrices'] = summarize_annual_tax_artifact_matrices(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_dossier(process, rule_set, source_bundle)
        summary['annual_tax_dossiers'] = summarize_annual_tax_dossiers(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2026,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': summary},
            paquete_ref='ddjj-package-stage6-controlled',
            responsable_revision_ref='stage6-review-owner-ddjj',
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2026,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_f22={'resumen_anual': summary, 'regimen_tributario': 'propyme-general-v1'},
            borrador_ref='f22-draft-stage6-controlled',
            responsable_revision_ref='stage6-review-owner-f22',
        )
        sync_annual_tax_export(process, rule_set, source_bundle)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        summary['annual_tax_review_checklists'] = summarize_annual_tax_review_checklists(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
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

    def _add_reviewed_f22_fixed_width_mapping_and_resync(self, *, code='1234', value='1000'):
        empresa = self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa, estado='activa')
        mapping_source = AnnualTaxOfficialSource.objects.filter(
            anio_tributario=process.anio_tributario,
            applies_to=DestinoMapeoTributarioAnual.F22,
            estado=EstadoAnnualTaxOfficialSource.APPROVED,
        ).order_by('id').first()
        if mapping_source is None:
            mapping_source = self._create_official_source(
                anio_tributario=process.anio_tributario,
                applies_to=DestinoMapeoTributarioAnual.F22,
                regime_code=config.regimen_tributario.codigo_regimen,
            )
        mapping = TaxCodeMapping.objects.create(
            rule_set=rule_set,
            destino=DestinoMapeoTributarioAnual.F22,
            codigo_interno=f'f22.controlled.{code}',
            codigo_destino=code,
            formula_ref=f'formula-ref-f22-{code}-controlled',
            evidencia_ref=f'sii-f22-at2026-code-{code}',
            official_source=mapping_source,
            metadata={
                'source': 'stage6-controlled',
                'f22_fixed_width_value': value,
                'f22_fixed_width_sign': '+',
                'f22_fixed_width_review_state': 'approved_for_candidate',
                'f22_value_source_ref': f'lm-reviewed-f22-value-{code}',
                'f22_responsible_review_ref': 'tax-reviewer-at2026-controlled',
            },
        )
        sync_annual_tax_artifact_matrix(process, rule_set, source_bundle, config)
        summary = process.resumen_anual
        summary['annual_tax_artifact_matrices'] = summarize_annual_tax_artifact_matrices(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_dossier(process, rule_set, source_bundle)
        summary['annual_tax_dossiers'] = summarize_annual_tax_dossiers(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_export(process, rule_set, source_bundle)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        return AnnualTaxExport.objects.get(), mapping

    def _artifact_matrix_item_hash(self, item):
        return hashlib.sha256(
            json.dumps(
                {
                    'matrix_id': item.matrix_id,
                    'target_kind': item.target_kind,
                    'target_code': item.target_code,
                    'medio_sii': item.medio_sii,
                    'source_kind': item.source_kind,
                    'source_model': item.source_model,
                    'source_object_id': item.source_object_id,
                    'source_hash': item.source_hash,
                    'review_state': item.review_state,
                    'formula_ref': item.formula_ref,
                    'evidencia_ref': item.evidencia_ref,
                    'responsible_ref': item.responsible_ref,
                    'warning_review_ref': item.warning_review_ref,
                    'warnings': item.warnings,
                    'source_payload': item.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()

    def _workbook_line_hash(self, line):
        return hashlib.sha256(
            json.dumps(
                {
                    'workbook_id': line.workbook_id,
                    'mapping_id': line.mapping_id,
                    'codigo_interno': line.codigo_interno,
                    'codigo_destino': line.codigo_destino,
                    'origen': line.origen,
                    'signo': line.signo,
                    'monto_clp': str(line.monto_clp),
                    'formula_ref': line.formula_ref,
                    'evidencia_ref': line.evidencia_ref,
                    'warning_review_ref': line.warning_review_ref,
                    'warnings': line.warnings,
                    'source_payload': line.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()

    def _enterprise_movement_hash(self, movement):
        return hashlib.sha256(
            json.dumps(
                {
                    'register_set_id': movement.register_set_id,
                    'source_workbook_line_id': movement.source_workbook_line_id,
                    'codigo_interno': movement.codigo_interno,
                    'origen': movement.origen,
                    'signo': movement.signo,
                    'monto_clp': str(movement.monto_clp),
                    'formula_ref': movement.formula_ref,
                    'evidencia_ref': movement.evidencia_ref,
                    'warning_review_ref': movement.warning_review_ref,
                    'warnings': movement.warnings,
                    'source_payload': movement.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()

    def _seed_generated_warning_review_candidates(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()

        line = AnnualTaxWorkbookLine.objects.select_related('workbook', 'mapping').get(workbook__tipo='RLI')
        line.warnings = ['source_metric_requires_responsible_review']
        line.warning_review_ref = ''
        line.hash_linea = self._workbook_line_hash(line)
        line.save(update_fields=['warnings', 'warning_review_ref', 'hash_linea', 'updated_at'])

        movement = AnnualEnterpriseRegisterMovement.objects.select_related('register_set').get(
            register_set__tipo_registro='RAI'
        )
        movement.warnings = ['movement_requires_responsible_review']
        movement.warning_review_ref = ''
        movement.hash_movimiento = self._enterprise_movement_hash(movement)
        movement.save(update_fields=['warnings', 'warning_review_ref', 'hash_movimiento', 'updated_at'])

        item = AnnualTaxArtifactMatrixItem.objects.select_related('matrix').get(
            target_kind='F22',
            target_code='F22-PREVIEW',
        )
        item.warnings = ['artifact_requires_responsible_review']
        item.review_state = EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
        item.warning_review_ref = ''
        item.hash_item = self._artifact_matrix_item_hash(item)
        item.save(update_fields=['warnings', 'review_state', 'warning_review_ref', 'hash_item', 'updated_at'])

        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_workbooks': summarize_annual_tax_workbooks(process),
            'annual_enterprise_registers': summarize_annual_enterprise_registers(process),
            'annual_tax_artifact_matrices': summarize_annual_tax_artifact_matrices(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])
        return process, line, movement, item

    def test_mark_generated_warnings_reviewed_dry_run_does_not_write(self):
        process, line, movement, item = self._seed_generated_warning_review_candidates()
        stdout = StringIO()

        call_command(
            'mark_annual_tax_generated_warnings_reviewed',
            process_id=process.id,
            warning_review_ref='tax-review-stage6-generated-chain-001',
            stdout=stdout,
        )
        result = json.loads(stdout.getvalue())
        line.refresh_from_db()
        movement.refresh_from_db()
        item.refresh_from_db()

        self.assertFalse(result['applied'])
        self.assertEqual(result['before']['pending_warnings_total'], 3)
        self.assertEqual(result['after']['pending_warnings_total'], 3)
        self.assertEqual(line.warning_review_ref, '')
        self.assertEqual(movement.warning_review_ref, '')
        self.assertEqual(item.warning_review_ref, '')
        self.assertEqual(item.review_state, EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW)

    def test_mark_generated_warnings_reviewed_rejects_sensitive_ref(self):
        process, _, _, _ = self._seed_generated_warning_review_candidates()

        with self.assertRaises(CommandError):
            call_command(
                'mark_annual_tax_generated_warnings_reviewed',
                process_id=process.id,
                warning_review_ref='https://sii.example.test/review?token=secret',
                apply=True,
                stdout=StringIO(),
            )

    def test_mark_generated_warnings_reviewed_apply_refreshes_review_chain(self):
        process, line, movement, item = self._seed_generated_warning_review_candidates()
        stdout = StringIO()

        call_command(
            'mark_annual_tax_generated_warnings_reviewed',
            process_id=process.id,
            warning_review_ref='tax-review-stage6-generated-chain-001',
            apply=True,
            fail_on_pending=True,
            stdout=stdout,
        )
        result = json.loads(stdout.getvalue())
        line.refresh_from_db()
        movement.refresh_from_db()
        item.refresh_from_db()
        process.refresh_from_db()
        checklist = AnnualTaxReviewChecklist.objects.get(proceso_renta_anual=process)
        stage6_result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in stage6_result['issues']}

        self.assertTrue(result['applied'])
        self.assertEqual(result['before']['pending_warnings_total'], 3)
        self.assertEqual(result['after']['pending_warnings_total'], 0)
        self.assertEqual(line.warning_review_ref, 'tax-review-stage6-generated-chain-001')
        self.assertEqual(movement.warning_review_ref, 'tax-review-stage6-generated-chain-001')
        self.assertEqual(item.warning_review_ref, 'tax-review-stage6-generated-chain-001')
        self.assertEqual(item.review_state, EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW)
        self.assertEqual(checklist.warnings_total, 0)
        self.assertEqual(checklist.completed_items_total, checklist.items_total)
        self.assertNotIn('stage6.tax_workbook_line_warning_review_required', issue_codes)
        self.assertNotIn('stage6.enterprise_register_movement_warning_review_required', issue_codes)
        self.assertNotIn('stage6.artifact_matrix_item_warning_review_required', issue_codes)
        self.assertNotIn('stage6.tax_dossier_review_required', issue_codes)
        self.assertNotIn('stage6.tax_export_review_required', issue_codes)
        self.assertNotIn('stage6.tax_review_checklist_incomplete', issue_codes)
        self.assertNotIn('stage6.tax_review_checklist_warning_review_required', issue_codes)

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

    def test_active_fiscal_config_with_unsupported_regime_is_blocking(self):
        empresa = self._create_active_empresa(nombre='UnsupportedStage6Co', rut='67676767-6')
        self._activate_unsupported_fiscal_config(empresa)

        result = collect_stage6_renta_anual_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.fiscal_config_unsupported_regime', issue_codes)
        self.assertNotIn('stage6.fiscal_config_missing', issue_codes)
        self.assertEqual(result['sections']['fiscal_setup']['active_configs'], 1)
        self.assertEqual(result['sections']['fiscal_setup']['unsupported_active_regime'], 1)
        self.assertEqual(
            result['sections']['fiscal_setup']['supported_regime_code'],
            'EmpresaContabilidadCompletaV1',
        )
        self.assertNotIn(empresa.rut, json.dumps(result))

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

    def test_annual_status_updated_event_without_review_responsible_is_blocking(self):
        AuditEvent.objects.create(
            event_type='sii.ddjj_preparacion.status_updated',
            entity_type='ddjj_preparacion',
            entity_id='1',
            summary='Actualizacion anual heredada sin responsable auditado.',
            metadata={
                'campo_estado': 'estado_preparacion',
                'estado_anterior': EstadoPreparacionTributaria.PREPARED,
                'estado_nuevo': EstadoPreparacionTributaria.APPROVED,
            },
        )

        result = collect_stage6_renta_anual_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertIn('stage6.audit.annual_status_responsible_ref_missing', issue_codes)
        self.assertEqual(result['sections']['audit']['annual_status_responsible_ref_missing'], 1)

    def test_annual_status_updated_event_with_sensitive_review_responsible_is_blocking_without_leak(self):
        AuditEvent.objects.create(
            event_type='sii.f22_preparacion.status_updated',
            entity_type='f22_preparacion',
            entity_id='1',
            summary='Actualizacion anual heredada con responsable sensible.',
            metadata={
                'campo_estado': 'estado_preparacion',
                'estado_anterior': EstadoPreparacionTributaria.PREPARED,
                'estado_nuevo': EstadoPreparacionTributaria.APPROVED,
                'responsable_revision_ref': 'https://sii.example.test/reviewer?token=secret',
            },
        )

        result = collect_stage6_renta_anual_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertIn('stage6.audit.annual_status_responsible_ref_sensitive', issue_codes)
        self.assertEqual(result['sections']['audit']['annual_status_responsible_ref_sensitive'], 1)
        self.assertNotIn('sii.example.test', serialized_result)
        self.assertNotIn('token=secret', serialized_result)

    def test_valid_authorized_matrix_and_non_sensitive_refs_can_pass_readiness(self):
        self._create_valid_local_matrix()

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage6_renta_anual'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertTrue(result['sections']['source_trace']['source_label'])
        self.assertTrue(result['sections']['source_trace']['authorization_ref'])
        self.assertEqual(result['issues'], [])

    def test_annual_process_without_trial_balance_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxTrialBalanceLine.objects.all().delete()
        AnnualTaxTrialBalance.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_trial_balance_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_trial_balances']['balances_total'], 0)

    def test_annual_trial_balance_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        trial_balance_summary = dict(summary['annual_tax_trial_balances'])
        by_id = dict(trial_balance_summary['by_id'])
        first_key = next(iter(by_id))
        first_summary = dict(by_id[first_key])
        first_summary['hash_balance'] = 'f' * 64
        by_id[first_key] = first_summary
        trial_balance_summary['by_id'] = by_id
        summary['annual_tax_trial_balances'] = trial_balance_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_trial_balance_summary_mismatch', issue_codes)

    def test_annual_trial_balance_line_warning_is_blocking(self):
        self._create_valid_local_matrix()
        line = AnnualTaxTrialBalanceLine.objects.select_related('trial_balance', 'cuenta_contable').get(
            clasificador_dj1847='RLI-LEASE-REVENUE'
        )
        line.warnings = ['dj1847_classifier_requires_review']
        line.hash_linea = hashlib.sha256(
            json.dumps(
                {
                    'trial_balance_id': line.trial_balance_id,
                    'cuenta_contable_id': line.cuenta_contable_id,
                    'codigo_cuenta': line.codigo_cuenta,
                    'nombre_cuenta': line.nombre_cuenta,
                    'clasificador_dj1847': line.clasificador_dj1847,
                    'sumas_debe_clp': str(line.sumas_debe_clp),
                    'sumas_haber_clp': str(line.sumas_haber_clp),
                    'saldo_deudor_clp': str(line.saldo_deudor_clp),
                    'saldo_acreedor_clp': str(line.saldo_acreedor_clp),
                    'inventario_activo_clp': str(line.inventario_activo_clp),
                    'inventario_pasivo_clp': str(line.inventario_pasivo_clp),
                    'resultado_perdida_clp': str(line.resultado_perdida_clp),
                    'resultado_ganancia_clp': str(line.resultado_ganancia_clp),
                    'formula_ref': line.formula_ref,
                    'evidencia_ref': line.evidencia_ref,
                    'warnings': line.warnings,
                    'source_payload': line.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        line.save(update_fields=['warnings', 'hash_linea', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.trial_balance_warning_review_required', issue_codes)

    def test_annual_process_without_tax_workbooks_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualEnterpriseRegisterSet.objects.all().delete()
        AnnualTaxWorkbook.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_workbooks_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_workbooks']['workbooks_total'], 0)

    def test_annual_tax_workbook_without_active_lines_is_blocking(self):
        self._create_valid_local_matrix()
        workbook = AnnualTaxWorkbook.objects.get(tipo='RLI')
        AnnualTaxWorkbookLine.objects.filter(workbook=workbook).update(estado=EstadoRegistro.INACTIVE)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_workbook_line_missing', issue_codes)

    def test_annual_tax_workbook_line_warning_is_blocking(self):
        self._create_valid_local_matrix()
        line = AnnualTaxWorkbookLine.objects.select_related('workbook', 'mapping').get(workbook__tipo='RLI')
        line.warnings = ['source_metric_missing_or_unsupported']
        line.hash_linea = hashlib.sha256(
            json.dumps(
                {
                    'workbook_id': line.workbook_id,
                    'mapping_id': line.mapping_id,
                    'codigo_interno': line.codigo_interno,
                    'codigo_destino': line.codigo_destino,
                    'origen': line.origen,
                    'signo': line.signo,
                    'monto_clp': str(line.monto_clp),
                    'formula_ref': line.formula_ref,
                    'evidencia_ref': line.evidencia_ref,
                    'warning_review_ref': line.warning_review_ref,
                    'warnings': line.warnings,
                    'source_payload': line.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        line.save(update_fields=['warnings', 'hash_linea', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_workbook_line_warning_review_required', issue_codes)

    def test_sensitive_annual_tax_workbook_warning_review_ref_remains_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        line = AnnualTaxWorkbookLine.objects.select_related('workbook', 'mapping').get(workbook__tipo='RLI')
        line.warnings = ['source_metric_missing_or_unsupported']
        line.warning_review_ref = 'https://sii.example.test/review?token=secret'
        line.hash_linea = hashlib.sha256(
            json.dumps(
                {
                    'workbook_id': line.workbook_id,
                    'mapping_id': line.mapping_id,
                    'codigo_interno': line.codigo_interno,
                    'codigo_destino': line.codigo_destino,
                    'origen': line.origen,
                    'signo': line.signo,
                    'monto_clp': str(line.monto_clp),
                    'formula_ref': line.formula_ref,
                    'evidencia_ref': line.evidencia_ref,
                    'warning_review_ref': line.warning_review_ref,
                    'warnings': line.warnings,
                    'source_payload': line.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        AnnualTaxWorkbookLine.objects.filter(pk=line.pk).update(
            warnings=line.warnings,
            warning_review_ref=line.warning_review_ref,
            hash_linea=line.hash_linea,
        )
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_workbooks': summarize_annual_tax_workbooks(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        workbook_summary = summarize_annual_tax_workbooks(process)['by_type']['RLI']

        self.assertEqual(workbook_summary['warnings_total'], 1)
        self.assertEqual(workbook_summary['warnings_reviewed_total'], 0)
        self.assertEqual(workbook_summary['warnings_pending_review_total'], 1)
        self.assertIn('stage6.tax_workbook_line_warning_review_required', issue_codes)
        self.assertNotIn('stage6.process_tax_workbook_summary_mismatch', issue_codes)

    def test_reviewed_annual_tax_workbook_line_warning_stops_blocking_workbooks(self):
        self._create_valid_local_matrix()
        line = AnnualTaxWorkbookLine.objects.select_related('workbook', 'mapping').get(workbook__tipo='RLI')
        line.warnings = ['source_metric_missing_or_unsupported']
        line.warning_review_ref = ''
        line.hash_linea = hashlib.sha256(
            json.dumps(
                {
                    'workbook_id': line.workbook_id,
                    'mapping_id': line.mapping_id,
                    'codigo_interno': line.codigo_interno,
                    'codigo_destino': line.codigo_destino,
                    'origen': line.origen,
                    'signo': line.signo,
                    'monto_clp': str(line.monto_clp),
                    'formula_ref': line.formula_ref,
                    'evidencia_ref': line.evidencia_ref,
                    'warning_review_ref': line.warning_review_ref,
                    'warnings': line.warnings,
                    'source_payload': line.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        line.save(update_fields=['warnings', 'warning_review_ref', 'hash_linea', 'updated_at'])

        process = ProcesoRentaAnual.objects.get()
        acknowledgement = mark_annual_tax_workbook_warnings_reviewed(
            process,
            warning_review_ref='tax-review-stage6-workbook-warning-001',
        )
        self.assertEqual(acknowledgement['reviewed_warnings_total'], 1)
        line.refresh_from_db()
        self.assertEqual(line.warning_review_ref, 'tax-review-stage6-workbook-warning-001')

        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_workbooks': summarize_annual_tax_workbooks(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])
        source_bundle = AnnualTaxSourceBundle.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_review_checklists': summarize_annual_tax_review_checklists(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        workbook_summary = summarize_annual_tax_workbooks(process)['by_type']['RLI']
        checklist = AnnualTaxReviewChecklist.objects.get()
        workbook_item = next(item for item in checklist.review_payload['items'] if item['code'] == 'workbooks_rli_cpt')

        self.assertEqual(workbook_summary['warnings_total'], 1)
        self.assertEqual(workbook_summary['warnings_reviewed_total'], 1)
        self.assertEqual(workbook_summary['warnings_pending_review_total'], 0)
        self.assertEqual(checklist.warnings_total, 0)
        self.assertEqual(workbook_item['status'], 'complete')
        self.assertEqual(workbook_item['details']['warnings_total'], 1)
        self.assertEqual(workbook_item['details']['warnings_pending_review_total'], 0)
        self.assertNotIn('stage6.tax_workbook_line_warning_review_required', issue_codes)
        self.assertNotIn('stage6.tax_review_checklist_warning_review_required', issue_codes)

    def test_annual_tax_workbook_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        workbook_summary = dict(summary['annual_tax_workbooks'])
        by_type = dict(workbook_summary['by_type'])
        rli_summary = dict(by_type['RLI'])
        rli_summary['hash_workbook'] = 'f' * 64
        by_type['RLI'] = rli_summary
        workbook_summary['by_type'] = by_type
        summary['annual_tax_workbooks'] = workbook_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_workbook_summary_mismatch', issue_codes)

    def test_invalid_annual_tax_workbook_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        workbook = AnnualTaxWorkbook.objects.get(tipo='RLI')
        line = AnnualTaxWorkbookLine.objects.get(workbook=workbook)
        AnnualTaxWorkbook.objects.filter(pk=workbook.pk).update(
            source_ref='https://sii.example.test/rli?token=secret',
            resumen_workbook={'api_key': 'secret'},
            hash_workbook='not-a-sha',
        )
        AnnualTaxWorkbookLine.objects.filter(pk=line.pk).update(
            evidencia_ref='https://sii.example.test/evidence?token=secret',
            source_payload={'access_token': 'secret'},
            hash_linea='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_workbook_invalid', issue_codes)
        self.assertIn('stage6.tax_workbook_line_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('access_token', serialized_result)

    def test_annual_process_without_enterprise_registers_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualEnterpriseRegisterSet.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_enterprise_registers_missing', issue_codes)
        self.assertEqual(result['sections']['annual_enterprise_registers']['registers_total'], 0)

    def test_enterprise_register_without_active_movements_is_blocking(self):
        self._create_valid_local_matrix()
        register = AnnualEnterpriseRegisterSet.objects.get(tipo_registro='RAI')
        AnnualEnterpriseRegisterMovement.objects.filter(register_set=register).update(estado=EstadoRegistro.INACTIVE)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.enterprise_register_movement_missing', issue_codes)

    def test_enterprise_register_movement_warning_is_blocking(self):
        self._create_valid_local_matrix()
        movement = AnnualEnterpriseRegisterMovement.objects.select_related('register_set').get(register_set__tipo_registro='RAI')
        movement.warnings = ['opening_balance_requires_expert_review']
        movement.hash_movimiento = hashlib.sha256(
            json.dumps(
                {
                    'register_set_id': movement.register_set_id,
                    'source_workbook_line_id': movement.source_workbook_line_id,
                    'codigo_interno': movement.codigo_interno,
                    'origen': movement.origen,
                    'signo': movement.signo,
                    'monto_clp': str(movement.monto_clp),
                    'formula_ref': movement.formula_ref,
                    'evidencia_ref': movement.evidencia_ref,
                    'warning_review_ref': movement.warning_review_ref,
                    'warnings': movement.warnings,
                    'source_payload': movement.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        movement.save(update_fields=['warnings', 'hash_movimiento', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.enterprise_register_movement_warning_review_required', issue_codes)

    def test_reviewed_enterprise_register_movement_warning_stops_blocking_registers(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        movement = AnnualEnterpriseRegisterMovement.objects.select_related('register_set').get(register_set__tipo_registro='RAI')
        movement.warnings = ['opening_balance_requires_expert_review']
        movement.hash_movimiento = hashlib.sha256(
            json.dumps(
                {
                    'register_set_id': movement.register_set_id,
                    'source_workbook_line_id': movement.source_workbook_line_id,
                    'codigo_interno': movement.codigo_interno,
                    'origen': movement.origen,
                    'signo': movement.signo,
                    'monto_clp': str(movement.monto_clp),
                    'formula_ref': movement.formula_ref,
                    'evidencia_ref': movement.evidencia_ref,
                    'warning_review_ref': movement.warning_review_ref,
                    'warnings': movement.warnings,
                    'source_payload': movement.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        movement.save(update_fields=['warnings', 'hash_movimiento', 'updated_at'])

        acknowledgement = mark_annual_enterprise_register_warnings_reviewed(
            process,
            warning_review_ref='tax-review-stage6-enterprise-warning-001',
        )
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_enterprise_registers': summarize_annual_enterprise_registers(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])
        source_bundle = AnnualTaxSourceBundle.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_review_checklists': summarize_annual_tax_review_checklists(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        movement.refresh_from_db()
        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        register_summary = summarize_annual_enterprise_registers(process)['by_type']['RAI']
        checklist = AnnualTaxReviewChecklist.objects.get()
        register_item = next(item for item in checklist.review_payload['items'] if item['code'] == 'enterprise_registers')

        self.assertEqual(acknowledgement['reviewed_warnings_total'], 1)
        self.assertEqual(acknowledgement['reviewed_movements_total'], 1)
        self.assertEqual(movement.warning_review_ref, 'tax-review-stage6-enterprise-warning-001')
        self.assertEqual(register_summary['warnings_total'], 1)
        self.assertEqual(register_summary['warnings_reviewed_total'], 1)
        self.assertEqual(register_summary['warnings_pending_review_total'], 0)
        self.assertEqual(checklist.warnings_total, 0)
        self.assertEqual(register_item['status'], 'complete')
        self.assertEqual(register_item['details']['warnings_total'], 1)
        self.assertEqual(register_item['details']['warnings_pending_review_total'], 0)
        self.assertNotIn('stage6.enterprise_register_movement_warning_review_required', issue_codes)
        self.assertNotIn('stage6.tax_review_checklist_warning_review_required', issue_codes)
        self.assertNotIn('stage6.process_enterprise_register_summary_mismatch', issue_codes)

    def test_sensitive_enterprise_register_warning_review_ref_remains_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        movement = AnnualEnterpriseRegisterMovement.objects.select_related('register_set').get(register_set__tipo_registro='RAI')
        movement.warnings = ['opening_balance_requires_expert_review']
        movement.warning_review_ref = 'https://sii.example.test/review?token=secret'
        movement.hash_movimiento = hashlib.sha256(
            json.dumps(
                {
                    'register_set_id': movement.register_set_id,
                    'source_workbook_line_id': movement.source_workbook_line_id,
                    'codigo_interno': movement.codigo_interno,
                    'origen': movement.origen,
                    'signo': movement.signo,
                    'monto_clp': str(movement.monto_clp),
                    'formula_ref': movement.formula_ref,
                    'evidencia_ref': movement.evidencia_ref,
                    'warning_review_ref': movement.warning_review_ref,
                    'warnings': movement.warnings,
                    'source_payload': movement.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        AnnualEnterpriseRegisterMovement.objects.filter(pk=movement.pk).update(
            warnings=movement.warnings,
            warning_review_ref=movement.warning_review_ref,
            hash_movimiento=movement.hash_movimiento,
        )
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_enterprise_registers': summarize_annual_enterprise_registers(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        register_summary = summarize_annual_enterprise_registers(process)['by_type']['RAI']

        self.assertEqual(register_summary['warnings_total'], 1)
        self.assertEqual(register_summary['warnings_reviewed_total'], 0)
        self.assertEqual(register_summary['warnings_pending_review_total'], 1)
        self.assertIn('stage6.enterprise_register_movement_warning_review_required', issue_codes)
        self.assertNotIn('stage6.process_enterprise_register_summary_mismatch', issue_codes)

    def test_enterprise_register_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        register_summary = dict(summary['annual_enterprise_registers'])
        by_type = dict(register_summary['by_type'])
        rai_summary = dict(by_type['RAI'])
        rai_summary['hash_registro'] = 'f' * 64
        by_type['RAI'] = rai_summary
        register_summary['by_type'] = by_type
        summary['annual_enterprise_registers'] = register_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_enterprise_register_summary_mismatch', issue_codes)

    def test_invalid_enterprise_register_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        register = AnnualEnterpriseRegisterSet.objects.get(tipo_registro='RAI')
        movement = AnnualEnterpriseRegisterMovement.objects.get(register_set=register)
        AnnualEnterpriseRegisterSet.objects.filter(pk=register.pk).update(
            source_ref='https://sii.example.test/rai?token=secret',
            resumen_registro={'api_key': 'secret'},
            hash_registro='not-a-sha',
        )
        AnnualEnterpriseRegisterMovement.objects.filter(pk=movement.pk).update(
            evidencia_ref='https://sii.example.test/movement?token=secret',
            source_payload={'access_token': 'secret-register-value'},
            hash_movimiento='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.enterprise_register_invalid', issue_codes)
        self.assertIn('stage6.enterprise_register_movement_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('access_token', serialized_result)

    def test_annual_process_without_real_estate_section_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualRealEstateSection.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_real_estate_section_missing', issue_codes)
        self.assertEqual(result['sections']['annual_real_estate_sections']['sections_total'], 0)

    def test_real_estate_section_without_active_items_is_blocking(self):
        self._create_valid_local_matrix()
        section = AnnualRealEstateSection.objects.get()
        AnnualRealEstateItem.objects.filter(section=section).update(estado=EstadoRegistro.INACTIVE)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.real_estate_item_missing', issue_codes)

    def test_real_estate_item_warning_is_blocking(self):
        self._create_valid_local_matrix()
        item = AnnualRealEstateItem.objects.select_related('section').get()
        item.warnings = ['contribuciones_requires_expert_review']
        item.hash_item = hashlib.sha256(
            json.dumps(
                {
                    'section_id': item.section_id,
                    'propiedad_id': item.propiedad_id,
                    'codigo_propiedad_snapshot': item.codigo_propiedad_snapshot,
                    'rol_avaluo_snapshot': item.rol_avaluo_snapshot,
                    'direccion_snapshot': item.direccion_snapshot,
                    'comuna_snapshot': item.comuna_snapshot,
                    'region_snapshot': item.region_snapshot,
                    'tipo_inmueble_snapshot': item.tipo_inmueble_snapshot,
                    'owner_tipo_snapshot': item.owner_tipo_snapshot,
                    'owner_id_snapshot': item.owner_id_snapshot,
                    'arriendo_devengado_clp': str(item.arriendo_devengado_clp),
                    'arriendo_conciliado_clp': str(item.arriendo_conciliado_clp),
                    'arriendo_facturable_clp': str(item.arriendo_facturable_clp),
                    'contribuciones_clp': str(item.contribuciones_clp),
                    'official_contribution_source_id': item.section.official_contribution_source_id,
                    'formula_ref': item.formula_ref,
                    'evidencia_ref': item.evidencia_ref,
                    'warnings': item.warnings,
                    'source_payload': item.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        item.save(update_fields=['warnings', 'hash_item', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.real_estate_item_warning_review_required', issue_codes)

    def test_real_estate_contribution_source_missing_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualRealEstateSection.objects.update(official_contribution_source=None)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.real_estate_contribution_source_missing', issue_codes)

    def test_real_estate_contribution_value_missing_is_blocking(self):
        self._create_valid_local_matrix()
        item = AnnualRealEstateItem.objects.select_related('section').get()
        item.warnings = ['contribuciones_value_not_loaded_v1']
        item.source_payload = {
            **item.source_payload,
            'contribuciones_loaded': False,
            'contribuciones_source': 'official_or_expert_review_missing_value',
        }
        item.hash_item = hashlib.sha256(
            json.dumps(
                {
                    'section_id': item.section_id,
                    'propiedad_id': item.propiedad_id,
                    'codigo_propiedad_snapshot': item.codigo_propiedad_snapshot,
                    'rol_avaluo_snapshot': item.rol_avaluo_snapshot,
                    'direccion_snapshot': item.direccion_snapshot,
                    'comuna_snapshot': item.comuna_snapshot,
                    'region_snapshot': item.region_snapshot,
                    'tipo_inmueble_snapshot': item.tipo_inmueble_snapshot,
                    'owner_tipo_snapshot': item.owner_tipo_snapshot,
                    'owner_id_snapshot': item.owner_id_snapshot,
                    'arriendo_devengado_clp': str(item.arriendo_devengado_clp),
                    'arriendo_conciliado_clp': str(item.arriendo_conciliado_clp),
                    'arriendo_facturable_clp': str(item.arriendo_facturable_clp),
                    'contribuciones_clp': str(item.contribuciones_clp),
                    'official_contribution_source_id': item.section.official_contribution_source_id,
                    'formula_ref': item.formula_ref,
                    'evidencia_ref': item.evidencia_ref,
                    'warnings': item.warnings,
                    'source_payload': item.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        item.save(update_fields=['warnings', 'source_payload', 'hash_item', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.real_estate_contribution_value_missing', issue_codes)

    def test_real_estate_section_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        real_estate_summary = dict(summary['annual_real_estate_sections'])
        by_id = dict(real_estate_summary['by_id'])
        section_id = next(iter(by_id.keys()))
        section_summary = dict(by_id[section_id])
        section_summary['hash_seccion'] = 'f' * 64
        by_id[section_id] = section_summary
        real_estate_summary['by_id'] = by_id
        summary['annual_real_estate_sections'] = real_estate_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_real_estate_section_summary_mismatch', issue_codes)

    def test_invalid_real_estate_section_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        section = AnnualRealEstateSection.objects.get()
        item = AnnualRealEstateItem.objects.get(section=section)
        AnnualRealEstateSection.objects.filter(pk=section.pk).update(
            source_ref='https://sii.example.test/real-estate?token=secret',
            resumen_seccion={'api_key': 'secret-real-estate'},
            hash_seccion='not-a-sha',
        )
        AnnualRealEstateItem.objects.filter(pk=item.pk).update(
            evidencia_ref='https://sii.example.test/property?token=secret',
            source_payload={'access_token': 'secret-real-estate-item'},
            hash_item='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.real_estate_section_invalid', issue_codes)
        self.assertIn('stage6.real_estate_item_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('access_token', serialized_result)

    def test_ddjj_layout_missing_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxDDJJFormLayout.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_ddjj_layout_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_ddjj_layouts']['layouts_total'], 0)

    def test_ddjj_layout_warning_is_blocking(self):
        self._create_valid_local_matrix()
        layout = AnnualTaxDDJJFormLayout.objects.get()
        layout.warnings = ['ddjj_layout_requires_expert_review']
        layout.hash_layout = layout.compute_hash_layout()
        layout.save(update_fields=['warnings', 'hash_layout', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.ddjj_layout_warning_review_required', issue_codes)

    def test_ddjj_layout_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        layout_summary = dict(summary['annual_tax_ddjj_layouts'])
        by_form_code = dict(layout_summary['by_form_code'])
        form_code = next(iter(by_form_code.keys()))
        form_summary = dict(by_form_code[form_code])
        form_summary['hash_layout'] = 'f' * 64
        by_form_code[form_code] = form_summary
        layout_summary['by_form_code'] = by_form_code
        summary['annual_tax_ddjj_layouts'] = layout_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_ddjj_layout_summary_mismatch', issue_codes)

    def test_invalid_ddjj_layout_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        layout = AnnualTaxDDJJFormLayout.objects.get()
        AnnualTaxDDJJFormLayout.objects.filter(pk=layout.pk).update(
            layout_ref='https://sii.example.test/ddjj-layout?token=secret',
            source_payload={'api_key': 'secret-ddjj-layout'},
            hash_layout='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.ddjj_layout_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)

    def test_f22_export_layout_missing_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxF22ExportLayout.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_f22_export_layout_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_f22_export_layouts']['layouts_total'], 0)

    def test_f22_export_layout_warning_is_blocking(self):
        self._create_valid_local_matrix()
        layout = AnnualTaxF22ExportLayout.objects.get()
        layout.warnings = ['f22_layout_requires_expert_review']
        layout.hash_layout = layout.compute_hash_layout()
        layout.save(update_fields=['warnings', 'hash_layout', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.f22_export_layout_warning_review_required', issue_codes)

    def test_f22_export_layout_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        layout_summary = dict(summary['annual_tax_f22_export_layouts'])
        by_form_code = dict(layout_summary['by_form_code'])
        form_summary = dict(by_form_code['F22'])
        form_summary['hash_layout'] = 'f' * 64
        by_form_code['F22'] = form_summary
        layout_summary['by_form_code'] = by_form_code
        summary['annual_tax_f22_export_layouts'] = layout_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_f22_export_layout_summary_mismatch', issue_codes)

    def test_invalid_f22_export_layout_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        layout = AnnualTaxF22ExportLayout.objects.get()
        AnnualTaxF22ExportLayout.objects.filter(pk=layout.pk).update(
            format_ref='https://sii.example.test/f22-layout?token=secret',
            source_payload={'api_key': 'secret-f22-layout', 'official_format': True},
            hash_layout='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.f22_export_layout_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)

    def test_annual_process_without_artifact_matrix_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxReviewChecklist.objects.all().delete()
        AnnualTaxExport.objects.all().delete()
        AnnualTaxDossier.objects.all().delete()
        AnnualTaxArtifactMatrix.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_artifact_matrix_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_artifact_matrices']['matrices_total'], 0)

    def test_artifact_matrix_without_active_items_is_blocking(self):
        self._create_valid_local_matrix()
        matrix = AnnualTaxArtifactMatrix.objects.get()
        AnnualTaxArtifactMatrixItem.objects.filter(matrix=matrix).update(estado=EstadoRegistro.INACTIVE)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.artifact_matrix_item_missing', issue_codes)
        self.assertIn('stage6.artifact_matrix_f22_item_missing', issue_codes)
        self.assertIn('stage6.artifact_matrix_ddjj_item_missing', issue_codes)

    def test_artifact_matrix_item_warning_is_blocking(self):
        self._create_valid_local_matrix()
        item = AnnualTaxArtifactMatrixItem.objects.select_related('matrix').get(target_kind='F22', target_code='F22-PREVIEW')
        item.warnings = ['artifact_requires_expert_review']
        item.review_state = EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
        item.hash_item = hashlib.sha256(
            json.dumps(
                {
                    'matrix_id': item.matrix_id,
                    'target_kind': item.target_kind,
                    'target_code': item.target_code,
                    'medio_sii': item.medio_sii,
                    'source_kind': item.source_kind,
                    'source_model': item.source_model,
                    'source_object_id': item.source_object_id,
                    'source_hash': item.source_hash,
                    'review_state': item.review_state,
                    'formula_ref': item.formula_ref,
                    'evidencia_ref': item.evidencia_ref,
                    'responsible_ref': item.responsible_ref,
                    'warning_review_ref': item.warning_review_ref,
                    'warnings': item.warnings,
                    'source_payload': item.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        item.save(update_fields=['warnings', 'review_state', 'hash_item', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.artifact_matrix_item_warning_review_required', issue_codes)

    def test_artifact_matrix_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        artifact_summary = dict(summary['annual_tax_artifact_matrices'])
        by_id = dict(artifact_summary['by_id'])
        matrix_id = next(iter(by_id.keys()))
        matrix_summary = dict(by_id[matrix_id])
        matrix_summary['hash_matriz'] = 'f' * 64
        by_id[matrix_id] = matrix_summary
        artifact_summary['by_id'] = by_id
        summary['annual_tax_artifact_matrices'] = artifact_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_artifact_matrix_summary_mismatch', issue_codes)

    def test_invalid_artifact_matrix_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        matrix = AnnualTaxArtifactMatrix.objects.get()
        item = AnnualTaxArtifactMatrixItem.objects.get(matrix=matrix, target_kind='F22', target_code='F22-PREVIEW')
        AnnualTaxArtifactMatrix.objects.filter(pk=matrix.pk).update(
            source_ref='https://sii.example.test/artifact-matrix?token=secret',
            resumen_matriz={'api_key': 'secret-artifact-matrix'},
            hash_matriz='not-a-sha',
        )
        AnnualTaxArtifactMatrixItem.objects.filter(pk=item.pk).update(
            evidencia_ref='https://sii.example.test/artifact-item?token=secret',
            source_payload={'access_token': 'secret-artifact-item'},
            hash_item='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.artifact_matrix_invalid', issue_codes)
        self.assertIn('stage6.artifact_matrix_item_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('access_token', serialized_result)

    def test_annual_process_without_tax_dossier_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxReviewChecklist.objects.all().delete()
        AnnualTaxExport.objects.all().delete()
        AnnualTaxDossier.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_dossier_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_dossiers']['dossiers_total'], 0)

    def test_tax_dossier_review_required_is_blocking(self):
        self._create_valid_local_matrix()
        item = AnnualTaxArtifactMatrixItem.objects.select_related('matrix').get(target_kind='F22', target_code='F22-PREVIEW')
        item.warnings = ['dossier_requires_expert_review']
        item.review_state = EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
        item.hash_item = hashlib.sha256(
            json.dumps(
                {
                    'matrix_id': item.matrix_id,
                    'target_kind': item.target_kind,
                    'target_code': item.target_code,
                    'medio_sii': item.medio_sii,
                    'source_kind': item.source_kind,
                    'source_model': item.source_model,
                    'source_object_id': item.source_object_id,
                    'source_hash': item.source_hash,
                    'review_state': item.review_state,
                    'formula_ref': item.formula_ref,
                    'evidencia_ref': item.evidencia_ref,
                    'responsible_ref': item.responsible_ref,
                    'warning_review_ref': item.warning_review_ref,
                    'warnings': item.warnings,
                    'source_payload': item.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        item.save(update_fields=['warnings', 'review_state', 'hash_item', 'updated_at'])
        process = ProcesoRentaAnual.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        sync_annual_tax_dossier(process, rule_set, source_bundle)
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_dossiers': summarize_annual_tax_dossiers(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_dossier_review_required', issue_codes)

    def test_reviewed_artifact_matrix_warning_stops_blocking_review_chain(self):
        self._create_valid_local_matrix()
        item = AnnualTaxArtifactMatrixItem.objects.select_related('matrix').get(target_kind='F22', target_code='F22-PREVIEW')
        item.warnings = ['artifact_requires_responsible_review']
        item.review_state = EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
        item.warning_review_ref = ''
        item.hash_item = hashlib.sha256(
            json.dumps(
                {
                    'matrix_id': item.matrix_id,
                    'target_kind': item.target_kind,
                    'target_code': item.target_code,
                    'medio_sii': item.medio_sii,
                    'source_kind': item.source_kind,
                    'source_model': item.source_model,
                    'source_object_id': item.source_object_id,
                    'source_hash': item.source_hash,
                    'review_state': item.review_state,
                    'formula_ref': item.formula_ref,
                    'evidencia_ref': item.evidencia_ref,
                    'responsible_ref': item.responsible_ref,
                    'warning_review_ref': item.warning_review_ref,
                    'warnings': item.warnings,
                    'source_payload': item.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        item.save(update_fields=['warnings', 'review_state', 'warning_review_ref', 'hash_item', 'updated_at'])

        process = ProcesoRentaAnual.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        matrix = item.matrix
        acknowledgement = mark_annual_tax_artifact_matrix_warnings_reviewed(
            matrix,
            warning_review_ref='tax-review-stage6-artifact-warning-001',
        )
        self.assertEqual(acknowledgement['reviewed_warnings_total'], 1)
        item.refresh_from_db()
        self.assertEqual(item.review_state, EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW)
        self.assertEqual(item.warning_review_ref, 'tax-review-stage6-artifact-warning-001')

        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_artifact_matrices': summarize_annual_tax_artifact_matrices(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_dossier(process, rule_set, source_bundle)
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_dossiers': summarize_annual_tax_dossiers(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_export(process, rule_set, source_bundle)
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_exports': summarize_annual_tax_exports(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_review_checklists': summarize_annual_tax_review_checklists(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        matrix_summary = next(iter(summarize_annual_tax_artifact_matrices(process)['by_id'].values()))
        dossier = AnnualTaxDossier.objects.get()
        annual_export = AnnualTaxExport.objects.get()
        checklist = AnnualTaxReviewChecklist.objects.get()

        self.assertEqual(matrix_summary['warnings_total'], 1)
        self.assertEqual(matrix_summary['warnings_reviewed_total'], 1)
        self.assertEqual(matrix_summary['warnings_pending_review_total'], 0)
        self.assertEqual(dossier.review_state, EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW)
        self.assertEqual(annual_export.review_state, EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW)
        self.assertEqual(checklist.warnings_total, 0)
        self.assertNotIn('stage6.artifact_matrix_item_warning_review_required', issue_codes)
        self.assertNotIn('stage6.tax_dossier_review_required', issue_codes)
        self.assertNotIn('stage6.tax_export_review_required', issue_codes)
        self.assertNotIn('stage6.tax_review_checklist_warning_review_required', issue_codes)

    def test_sensitive_artifact_matrix_warning_review_ref_remains_blocking(self):
        self._create_valid_local_matrix()
        item = AnnualTaxArtifactMatrixItem.objects.select_related('matrix').get(target_kind='F22', target_code='F22-PREVIEW')
        item.warnings = ['artifact_requires_responsible_review']
        item.review_state = EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW
        item.warning_review_ref = 'https://sii.example.test/artifact-review?token=secret'
        item.hash_item = self._artifact_matrix_item_hash(item)
        item.save(update_fields=['warnings', 'review_state', 'warning_review_ref', 'hash_item', 'updated_at'])

        process = ProcesoRentaAnual.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_artifact_matrices': summarize_annual_tax_artifact_matrices(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])
        with self.assertRaisesMessage(ValueError, 'resumen_dossier no debe contener URLs'):
            sync_annual_tax_dossier(process, rule_set, source_bundle)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)
        matrix_summary = next(iter(summarize_annual_tax_artifact_matrices(process)['by_id'].values()))

        self.assertEqual(matrix_summary['warnings_total'], 1)
        self.assertEqual(matrix_summary['warnings_reviewed_total'], 0)
        self.assertEqual(matrix_summary['warnings_pending_review_total'], 1)
        self.assertIn('stage6.artifact_matrix_item_invalid', issue_codes)
        self.assertIn('stage6.artifact_matrix_item_warning_review_required', issue_codes)
        self.assertNotIn('token=secret', serialized_result)

    def test_tax_dossier_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        dossier_summary = dict(summary['annual_tax_dossiers'])
        by_id = dict(dossier_summary['by_id'])
        dossier_id = next(iter(by_id.keys()))
        item_summary = dict(by_id[dossier_id])
        item_summary['hash_dossier'] = 'f' * 64
        by_id[dossier_id] = item_summary
        dossier_summary['by_id'] = by_id
        summary['annual_tax_dossiers'] = dossier_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_dossier_summary_mismatch', issue_codes)

    def test_invalid_tax_dossier_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxDossier.objects.update(
            source_ref='https://sii.example.test/dossier?token=secret',
            responsible_ref='Bearer tax-dossier-secret',
            dossier_ref='https://sii.example.test/dossier-file?token=secret',
            resumen_dossier={'api_key': 'secret-tax-dossier'},
            hash_dossier='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_dossier_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('tax-dossier-secret', serialized_result)

    def test_tax_dossier_boundary_flags_are_blocking(self):
        self._create_valid_local_matrix()
        dossier = AnnualTaxDossier.objects.get()
        process = dossier.proceso_renta_anual
        dossier_summary = dict(dossier.resumen_dossier)
        dossier_summary.update(
            {
                'official_format': True,
                'sii_submission': True,
                'sii_submission_attempted': True,
                'final_tax_calculation': True,
            }
        )
        hash_dossier = hashlib.sha256(
            json.dumps(
                dossier_summary,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        AnnualTaxDossier.objects.filter(pk=dossier.pk).update(
            resumen_dossier=dossier_summary,
            hash_dossier=hash_dossier,
        )
        process_summary = dict(process.resumen_anual)
        dossier_process_summary = dict(process_summary['annual_tax_dossiers'])
        by_id = dict(dossier_process_summary['by_id'])
        item_summary = dict(by_id[str(dossier.id)])
        item_summary['hash_dossier'] = hash_dossier
        by_id[str(dossier.id)] = item_summary
        dossier_process_summary['by_id'] = by_id
        process_summary['annual_tax_dossiers'] = dossier_process_summary
        process.resumen_anual = process_summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_dossier_invalid', issue_codes)
        self.assertIn('stage6.tax_dossier_official_format_boundary', issue_codes)
        self.assertIn('stage6.tax_dossier_sii_submission_boundary', issue_codes)
        self.assertIn('stage6.tax_dossier_final_calculation_boundary', issue_codes)

    def test_annual_process_without_tax_export_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxReviewChecklist.objects.all().delete()
        AnnualTaxExport.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_export_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_exports']['exports_total'], 0)

    def test_tax_export_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        export_summary = dict(summary['annual_tax_exports'])
        by_id = dict(export_summary['by_id'])
        export_id = next(iter(by_id.keys()))
        item_summary = dict(by_id[export_id])
        item_summary['hash_export'] = 'f' * 64
        by_id[export_id] = item_summary
        export_summary['by_id'] = by_id
        summary['annual_tax_exports'] = export_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_export_summary_mismatch', issue_codes)

    def test_tax_export_without_f22_format_source_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        export = AnnualTaxExport.objects.get()
        payload = dict(export.export_payload)
        payload['official_format_source_id'] = None
        payload['official_format_source'] = {
            'source': 'not_loaded_v1',
            'official_source_id': None,
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
            'requires_official_format_gate': True,
            'requires_explicit_submission_authorization': True,
        }
        hash_export = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')
        ).hexdigest()
        AnnualTaxExport.objects.filter(pk=export.pk).update(
            official_format_source=None,
            export_payload=payload,
            hash_export=hash_export,
        )
        summary = dict(process.resumen_anual)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_export_official_format_source_missing', issue_codes)

    def test_tax_export_emits_structural_artifact_contracts(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        payload = export.export_payload
        contracts = payload['export_artifact_contracts']
        file_manifest = payload['export_file_manifest']
        package_manifest = payload['export_file_package_manifest']

        self.assertEqual(payload['export_contracts_total'], export.target_items_total)
        self.assertEqual(payload['ddjj_export_contracts_total'], export.ddjj_items_total)
        self.assertEqual(payload['f22_export_contracts_total'], export.f22_items_total)
        self.assertEqual(payload['export_files_total'], export.target_items_total)
        self.assertEqual(payload['ddjj_export_files_total'], export.ddjj_items_total)
        self.assertEqual(payload['f22_export_files_total'], export.f22_items_total)
        self.assertRegex(payload['export_file_manifest_hash'], r'^[0-9a-f]{64}$')
        self.assertEqual(payload['export_file_package_version'], 'annual-tax-export-file-package-v1')
        self.assertEqual(payload['export_file_package_files_total'], export.target_items_total)
        self.assertEqual(payload['ddjj_export_package_files_total'], export.ddjj_items_total)
        self.assertEqual(payload['f22_export_package_files_total'], export.f22_items_total)
        self.assertRegex(payload['export_file_package_hash'], r'^[0-9a-f]{64}$')
        self.assertEqual(len(contracts), export.target_items_total)
        self.assertEqual(len(file_manifest), export.target_items_total)
        self.assertEqual(len(package_manifest), export.target_items_total)
        self.assertEqual(
            sum(1 for contract in contracts if contract['target_kind'] == 'DDJJ'),
            export.ddjj_items_total,
        )
        self.assertEqual(
            sum(1 for contract in contracts if contract['target_kind'] == 'F22'),
            export.f22_items_total,
        )
        for contract in contracts:
            self.assertEqual(contract['contract_version'], 'annual-tax-export-artifact-contract-v1')
            self.assertEqual(contract['delivery_kind'], 'local_controlled_preview')
            self.assertFalse(contract['official_format'])
            self.assertFalse(contract['sii_submission'])
            self.assertFalse(contract['final_tax_calculation'])
            self.assertTrue(contract['requires_official_format_gate'])
            self.assertTrue(contract['requires_explicit_submission_authorization'])
        self.assertEqual(
            {str(contract['artifact_matrix_item_id']) for contract in contracts},
            {str(entry['artifact_matrix_item_id']) for entry in file_manifest},
        )
        self.assertEqual(
            {str(entry['artifact_matrix_item_id']) for entry in file_manifest},
            {str(entry['artifact_matrix_item_id']) for entry in package_manifest},
        )
        for entry in file_manifest:
            self.assertEqual(entry['file_manifest_version'], 'annual-tax-export-file-manifest-v1')
            self.assertEqual(entry['delivery_kind'], 'local_controlled_export_file')
            self.assertEqual(entry['content_type'], 'application/json')
            self.assertEqual(entry['encoding'], 'utf-8')
            self.assertEqual(entry['schema_ref'], 'annual-tax-export-file-payload-v1')
            self.assertTrue(entry['file_name'].endswith('.json'))
            self.assertRegex(entry['payload_hash'], r'^[0-9a-f]{64}$')
            self.assertGreater(entry['payload_size_bytes'], 0)
            self.assertFalse(entry['official_format'])
            self.assertFalse(entry['sii_submission'])
            self.assertFalse(entry['final_tax_calculation'])
        for entry in package_manifest:
            self.assertEqual(entry['package_entry_version'], 'annual-tax-export-file-package-manifest-v1')
            self.assertEqual(entry['delivery_kind'], 'local_controlled_export_package')
            self.assertEqual(entry['materialized_from'], 'annual-tax-export-file-payload-v1')
            self.assertEqual(entry['canonical_json'], 'sort_keys_ascii_compact')
            self.assertEqual(entry['content_type'], 'application/json')
            self.assertEqual(entry['encoding'], 'utf-8')
            self.assertEqual(entry['schema_ref'], 'annual-tax-export-file-payload-v1')
            self.assertTrue(entry['file_name'].endswith('.json'))
            self.assertRegex(entry['payload_hash'], r'^[0-9a-f]{64}$')
            self.assertEqual(entry['payload_hash'], entry['manifest_payload_hash'])
            self.assertEqual(entry['payload_size_bytes'], entry['manifest_payload_size_bytes'])
            self.assertGreater(entry['payload_size_bytes'], 0)
            self.assertFalse(entry['official_format'])
            self.assertFalse(entry['sii_submission'])
            self.assertFalse(entry['final_tax_calculation'])

        package = build_annual_tax_export_file_package(export)
        self.assertEqual(package['summary']['package_version'], 'annual-tax-export-file-package-v1')
        self.assertEqual(package['summary']['files_total'], export.target_items_total)
        self.assertEqual(package['summary']['export_file_package_hash'], payload['export_file_package_hash'])
        self.assertEqual(len(package['files']), export.target_items_total)
        for file_item in package['files']:
            encoded_content = file_item['content'].encode(file_item['encoding'])
            self.assertEqual(hashlib.sha256(encoded_content).hexdigest(), file_item['payload_hash'])
            self.assertEqual(len(encoded_content), file_item['payload_size_bytes'])
            self.assertEqual(json.loads(file_item['content'])['schema'], 'annual-tax-export-file-payload-v1')
            self.assertFalse(json.loads(file_item['content'])['official_format'])
            self.assertFalse(json.loads(file_item['content'])['sii_submission'])
            self.assertFalse(json.loads(file_item['content'])['final_tax_calculation'])
        with TemporaryDirectory() as temp_dir:
            written = write_annual_tax_export_file_package(export, temp_dir)
            self.assertEqual(len(written['written_files']), export.target_items_total)
            self.assertTrue(Path(written['manifest_file']).exists())
            manifest_payload = json.loads(Path(written['manifest_file']).read_text(encoding='utf-8'))
            self.assertEqual(manifest_payload['summary']['export_file_package_hash'], payload['export_file_package_hash'])
            for file_path in written['written_files']:
                path = Path(file_path)
                self.assertTrue(path.exists())
                file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertIn(file_hash, package['summary']['file_hashes'])
            verification = verify_annual_tax_export_file_package(export, temp_dir)
            self.assertTrue(verification['verified'])
            self.assertTrue(verification['ready_for_responsible_review'])
            self.assertEqual(verification['files_total'], export.target_items_total)
            self.assertEqual(verification['package_hash'], payload['export_file_package_hash'])
            self.assertFalse(verification['official_format'])
            self.assertFalse(verification['sii_submission'])
            self.assertFalse(verification['final_tax_calculation'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        self.assertNotIn('stage6.tax_export_artifact_contracts_missing', issue_codes)
        self.assertNotIn('stage6.tax_export_artifact_contracts_mismatch', issue_codes)
        self.assertNotIn('stage6.tax_export_artifact_contracts_invalid', issue_codes)
        self.assertNotIn('stage6.tax_export_artifact_contract_boundary', issue_codes)
        self.assertNotIn('stage6.tax_export_file_manifest_missing', issue_codes)
        self.assertNotIn('stage6.tax_export_file_manifest_mismatch', issue_codes)
        self.assertNotIn('stage6.tax_export_file_manifest_invalid', issue_codes)
        self.assertNotIn('stage6.tax_export_file_manifest_boundary', issue_codes)
        self.assertNotIn('stage6.tax_export_file_package_missing', issue_codes)
        self.assertNotIn('stage6.tax_export_file_package_mismatch', issue_codes)
        self.assertNotIn('stage6.tax_export_file_package_invalid', issue_codes)
        self.assertNotIn('stage6.tax_export_file_package_boundary', issue_codes)

    def test_tax_export_writes_verifiable_ddjj_ascii_candidate_from_reviewed_records(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)

        candidate = build_annual_tax_ddjj_ascii_export_candidate(
            export,
            form_code='1887',
            rut_number='97030000',
            records=[
                {
                    'record': '1' + 'A' * 23,
                    'review_state': 'approved_for_candidate',
                    'record_source_ref': 'lm-ddjj-1887-header-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                    'artifact_matrix_item_id': ddjj_item.id,
                    'hash_item': ddjj_item.hash_item,
                },
                {
                    'record': '2' + 'B' * 23,
                    'review_state': 'approved_for_candidate',
                    'record_source_ref': 'lm-ddjj-1887-detail-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                    'artifact_matrix_item_id': ddjj_item.id,
                    'hash_item': ddjj_item.hash_item,
                },
                {
                    'record': '3' + 'C' * 23,
                    'review_state': 'approved_for_candidate',
                    'record_source_ref': 'lm-ddjj-1887-summary-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                    'artifact_matrix_item_id': ddjj_item.id,
                    'hash_item': ddjj_item.hash_item,
                },
            ],
        )

        summary = candidate['summary']
        self.assertEqual(summary['candidate_version'], 'annual-tax-ddjj-ascii-candidate-v1')
        self.assertEqual(summary['record_format_kind'], 'ascii_fixed_width_positional')
        self.assertEqual(summary['form_code'], '1887')
        self.assertEqual(summary['file_name'], '97030000.887')
        self.assertEqual(summary['record_length'], 24)
        self.assertEqual(summary['records_total'], 3)
        self.assertEqual(summary['record_type_counts'], {'1': 1, '2': 1, '3': 1})
        self.assertEqual(summary['ddjj_record_review_evidence_total'], 3)
        self.assertEqual(len(summary['artifact_matrix_item_ids']), 1)
        self.assertIn(ddjj_item.id, summary['artifact_matrix_item_ids'])
        self.assertTrue(summary['zip_required_for_submission'])
        self.assertFalse(summary['official_format'])
        self.assertFalse(summary['sii_submission'])
        self.assertFalse(summary['final_tax_calculation'])
        self.assertEqual(candidate['records'], ['1' + 'A' * 23, '2' + 'B' * 23, '3' + 'C' * 23])

        with TemporaryDirectory() as temp_dir:
            written = write_annual_tax_ddjj_ascii_export_candidate(candidate, temp_dir)
            self.assertTrue(Path(written['written_file']).exists())
            self.assertTrue(Path(written['manifest_file']).exists())
            verification = verify_annual_tax_ddjj_ascii_export_candidate(candidate, temp_dir)

        self.assertTrue(verification['verified'])
        self.assertTrue(verification['ready_for_responsible_review'])
        self.assertEqual(verification['records_total'], 3)
        self.assertEqual(verification['record_length'], 24)
        self.assertEqual(verification['file_name'], '97030000.887')
        self.assertFalse(verification['official_format'])
        self.assertFalse(verification['sii_submission'])
        self.assertFalse(verification['final_tax_calculation'])

        with TemporaryDirectory() as temp_dir:
            written = write_annual_tax_ddjj_ascii_export_candidate(candidate, temp_dir)
            Path(written['written_file']).write_text('1' + 'Z' * 23 + '\n', encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'hash esperado'):
                verify_annual_tax_ddjj_ascii_export_candidate(candidate, temp_dir)

    def test_tax_export_ddjj_ascii_candidate_rejects_invalid_layout_or_records(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        base_records = [
            {
                'record': '1' + 'A' * 23,
                'review_state': 'approved_for_candidate',
                'record_source_ref': 'lm-ddjj-1887-header-reviewed',
                'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                'artifact_matrix_item_id': ddjj_item.id,
                'hash_item': ddjj_item.hash_item,
            },
            {
                'record': '2' + 'B' * 23,
                'review_state': 'approved_for_candidate',
                'record_source_ref': 'lm-ddjj-1887-detail-reviewed',
                'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                'artifact_matrix_item_id': ddjj_item.id,
                'hash_item': ddjj_item.hash_item,
            },
            {
                'record': '3' + 'C' * 23,
                'review_state': 'approved_for_candidate',
                'record_source_ref': 'lm-ddjj-1887-summary-reviewed',
                'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                'artifact_matrix_item_id': ddjj_item.id,
                'hash_item': ddjj_item.hash_item,
            },
        ]

        with self.assertRaisesRegex(ValueError, 'largo del layout'):
            build_annual_tax_ddjj_ascii_export_candidate(
                export,
                form_code='1887',
                rut_number='97030000',
                records=[
                    {
                        **base_records[0],
                        'record': '1' + 'A' * 22,
                    },
                    base_records[1],
                    base_records[2],
                ],
            )

        with self.assertRaisesRegex(ValueError, 'tipo 2 de detalle'):
            build_annual_tax_ddjj_ascii_export_candidate(
                export,
                form_code='1887',
                rut_number='97030000',
                records=[
                    base_records[0],
                    base_records[2],
                ],
            )

        with self.assertRaisesRegex(ValueError, 'tipo 1 inicial'):
            build_annual_tax_ddjj_ascii_export_candidate(
                export,
                form_code='1887',
                rut_number='97030000',
                records=[
                    base_records[1],
                    base_records[1],
                    base_records[2],
                ],
            )

        with self.assertRaisesRegex(ValueError, 'record_source_ref no sensible'):
            build_annual_tax_ddjj_ascii_export_candidate(
                export,
                form_code='1887',
                rut_number='97030000',
                records=[
                    {
                        **base_records[0],
                        'record_source_ref': 'https://sii.example.test/ddjj?token=secret',
                    },
                    base_records[1],
                    base_records[2],
                ],
            )

        with self.assertRaisesRegex(ValueError, 'item de matriz ajeno al export'):
            build_annual_tax_ddjj_ascii_export_candidate(
                export,
                form_code='1887',
                rut_number='97030000',
                records=[
                    {
                        **base_records[0],
                        'artifact_matrix_item_id': ddjj_item.id + 999,
                    },
                    base_records[1],
                    base_records[2],
                ],
            )

        layout = AnnualTaxDDJJFormLayout.objects.get(form_code='1887')
        payload = dict(layout.source_payload)
        payload.pop('ddjj_ascii_record_length')
        payload.pop('record_format_kind')
        layout.source_payload = payload
        layout.hash_layout = layout.compute_hash_layout()
        layout.full_clean()
        layout.save()

        with self.assertRaisesRegex(ValueError, 'formato ASCII posicional revisado'):
            build_annual_tax_ddjj_ascii_export_candidate(
                export,
                form_code='1887',
                rut_number='97030000',
                records=base_records,
            )

    def _ddjj_ascii_records(self, ddjj_item):
        return [
                {
                    'record': '1' + 'A' * 23,
                    'review_state': 'approved_for_candidate',
                    'record_source_ref': 'lm-ddjj-1887-header-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                    'artifact_matrix_item_id': ddjj_item.id,
                    'hash_item': ddjj_item.hash_item,
                },
                {
                    'record': '2' + 'B' * 23,
                    'review_state': 'approved_for_candidate',
                    'record_source_ref': 'lm-ddjj-1887-detail-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                    'artifact_matrix_item_id': ddjj_item.id,
                    'hash_item': ddjj_item.hash_item,
                },
                {
                    'record': '3' + 'C' * 23,
                    'review_state': 'approved_for_candidate',
                    'record_source_ref': 'lm-ddjj-1887-summary-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                    'artifact_matrix_item_id': ddjj_item.id,
                    'hash_item': ddjj_item.hash_item,
                },
            ]

    def _build_ddjj_ascii_candidate_for_zip(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        return build_annual_tax_ddjj_ascii_export_candidate(
            export,
            form_code='1887',
            rut_number='97030000',
            records=self._ddjj_ascii_records(ddjj_item),
        )

    def _materialize_presentation_review_inputs(self, root_dir):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
        process = ProcesoRentaAnual.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        export.refresh_from_db()

        export_package_dir = Path(root_dir) / 'annual-export-package'
        write_annual_tax_export_file_package(export, export_package_dir)

        f22_dir = Path(root_dir) / 'f22-fixed-width-candidate'
        f22_candidate = build_annual_tax_f22_fixed_width_export_candidate(
            export,
            rut_number='11111111',
            rut_dv='1',
            company_code='QA',
            client_number='123456',
            entries=build_f22_fixed_width_entries_from_artifact_matrix(export),
            **self._f22_local_certification_kwargs(),
        )
        write_annual_tax_f22_fixed_width_export_candidate(f22_candidate, f22_dir)

        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        records = self._ddjj_ascii_records(ddjj_item)
        ddjj_ascii_candidate = build_annual_tax_ddjj_ascii_export_candidate(
            export,
            form_code='1887',
            rut_number='97030000',
            records=records,
        )
        ddjj_ascii_dir = Path(root_dir) / 'ddjj-ascii-candidate'
        write_annual_tax_ddjj_ascii_export_candidate(ddjj_ascii_candidate, ddjj_ascii_dir)

        ddjj_zip_candidate = build_annual_tax_ddjj_zip_export_candidate(
            ddjj_ascii_candidate,
            transfer_control_record={
                'record': '0' + 'T' * 23,
                'review_state': 'approved_for_candidate',
                'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                'responsible_review_ref': 'tax-reviewer-at2026-controlled',
            },
        )
        ddjj_zip_dir = Path(root_dir) / 'ddjj-zip-candidate'
        write_annual_tax_ddjj_zip_export_candidate(ddjj_zip_candidate, ddjj_zip_dir)

        return {
            'export': export,
            'export_package_dir': export_package_dir,
            'f22_dir': f22_dir,
            'ddjj_ascii_dir': ddjj_ascii_dir,
            'ddjj_zip_dir': ddjj_zip_dir,
        }

    def test_tax_export_writes_verifiable_ddjj_zip_candidate_from_ascii_candidate(self):
        ascii_candidate = self._build_ddjj_ascii_candidate_for_zip()
        zip_candidate = build_annual_tax_ddjj_zip_export_candidate(
            ascii_candidate,
            transfer_control_record={
                'record': '0' + 'T' * 23,
                'review_state': 'approved_for_candidate',
                'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                'responsible_review_ref': 'tax-reviewer-at2026-controlled',
            },
        )

        summary = zip_candidate['summary']
        self.assertEqual(summary['candidate_version'], 'annual-tax-ddjj-zip-candidate-v1')
        self.assertEqual(summary['source_candidate_version'], 'annual-tax-ddjj-ascii-candidate-v1')
        self.assertEqual(summary['record_format_kind'], 'ascii_fixed_width_positional_zip_candidate')
        self.assertEqual(summary['zip_entry_name'], '97030000.887')
        self.assertEqual(summary['zip_file_name'], '97030000.887.zip')
        self.assertEqual(summary['record_type_counts'], {'0': 1, '1': 1, '2': 1, '3': 1})
        self.assertEqual(zip_candidate['records'], ['0' + 'T' * 23, '1' + 'A' * 23, '2' + 'B' * 23, '3' + 'C' * 23])
        self.assertTrue(summary['zip_candidate_validated'])
        self.assertTrue(summary['requires_official_zip_gate'])
        self.assertFalse(summary['official_format'])
        self.assertFalse(summary['sii_submission'])
        self.assertFalse(summary['final_tax_calculation'])

        with TemporaryDirectory() as temp_dir:
            written = write_annual_tax_ddjj_zip_export_candidate(zip_candidate, temp_dir)
            self.assertTrue(Path(written['written_zip_file']).exists())
            self.assertTrue(Path(written['manifest_file']).exists())
            verification = verify_annual_tax_ddjj_zip_export_candidate(zip_candidate, temp_dir)
            with zipfile.ZipFile(written['written_zip_file'], mode='r') as archive:
                self.assertEqual(archive.namelist(), ['97030000.887'])

        self.assertTrue(verification['verified'])
        self.assertTrue(verification['ready_for_responsible_review'])
        self.assertFalse(verification['ready_for_submission'])
        self.assertEqual(verification['records_total'], 4)
        self.assertEqual(verification['record_length'], 24)
        self.assertEqual(verification['zip_file_name'], '97030000.887.zip')
        self.assertFalse(verification['official_format'])
        self.assertFalse(verification['sii_submission'])
        self.assertFalse(verification['final_tax_calculation'])

        with TemporaryDirectory() as temp_dir:
            written = write_annual_tax_ddjj_zip_export_candidate(zip_candidate, temp_dir)
            tampered_candidate = {
                **zip_candidate,
                'summary': {
                    **zip_candidate['summary'],
                    'zip_file_hash': '0' * 64,
                },
            }
            Path(written['manifest_file']).write_text(
                json.dumps(
                    {'summary': tampered_candidate['summary']},
                    sort_keys=True,
                    separators=(',', ':'),
                    ensure_ascii=True,
                    default=str,
                ),
                encoding='utf-8',
            )
            with self.assertRaisesRegex(ValueError, 'hash esperado'):
                verify_annual_tax_ddjj_zip_export_candidate(tampered_candidate, temp_dir)

        with TemporaryDirectory() as temp_dir:
            written = write_annual_tax_ddjj_zip_export_candidate(zip_candidate, temp_dir)
            with zipfile.ZipFile(written['written_zip_file'], mode='w', compression=zipfile.ZIP_STORED) as archive:
                archive.writestr('97030000.887', zip_candidate['content'].encode('ascii'))
            with self.assertRaisesRegex(ValueError, 'ZIP canonico esperado'):
                verify_annual_tax_ddjj_zip_export_candidate(zip_candidate, temp_dir)

    def test_tax_export_candidate_writers_reject_nonempty_output_dirs(self):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        ascii_candidate = build_annual_tax_ddjj_ascii_export_candidate(
            export,
            form_code='1887',
            rut_number='97030000',
            records=[
                {
                    'record': '1' + 'A' * 23,
                    'review_state': 'approved_for_candidate',
                    'record_source_ref': 'lm-ddjj-1887-header-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                    'artifact_matrix_item_id': ddjj_item.id,
                    'hash_item': ddjj_item.hash_item,
                },
                {
                    'record': '2' + 'B' * 23,
                    'review_state': 'approved_for_candidate',
                    'record_source_ref': 'lm-ddjj-1887-detail-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                    'artifact_matrix_item_id': ddjj_item.id,
                    'hash_item': ddjj_item.hash_item,
                },
                {
                    'record': '3' + 'C' * 23,
                    'review_state': 'approved_for_candidate',
                    'record_source_ref': 'lm-ddjj-1887-summary-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                    'artifact_matrix_item_id': ddjj_item.id,
                    'hash_item': ddjj_item.hash_item,
                },
            ],
        )
        zip_candidate = build_annual_tax_ddjj_zip_export_candidate(
            ascii_candidate,
            transfer_control_record={
                'record': '0' + 'T' * 23,
                'review_state': 'approved_for_candidate',
                'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                'responsible_review_ref': 'tax-reviewer-at2026-controlled',
            },
        )
        f22_candidate = build_annual_tax_f22_fixed_width_export_candidate(
            export,
            rut_number='11111111',
            rut_dv='1',
            company_code='QA',
            client_number='123456',
            **self._f22_local_certification_kwargs(),
            entries=build_f22_fixed_width_entries_from_artifact_matrix(export),
        )

        for writer, candidate, manifest_name in (
            (
                write_annual_tax_ddjj_ascii_export_candidate,
                ascii_candidate,
                'ddjj-ascii-candidate-manifest.json',
            ),
            (
                write_annual_tax_ddjj_zip_export_candidate,
                zip_candidate,
                'ddjj-zip-candidate-manifest.json',
            ),
            (
                write_annual_tax_f22_fixed_width_export_candidate,
                f22_candidate,
                'f22-fixed-width-candidate-manifest.json',
            ),
        ):
            with self.subTest(writer=writer.__name__), TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir) / 'candidate-output'
                output_dir.mkdir()
                stale_file = output_dir / 'stale.txt'
                stale_file.write_text('stale-evidence', encoding='utf-8')

                with self.assertRaisesRegex(ValueError, 'debe estar vacio'):
                    writer(candidate, output_dir)

                self.assertEqual(stale_file.read_text(encoding='utf-8'), 'stale-evidence')
                self.assertFalse((output_dir / manifest_name).exists())

    def test_tax_export_ddjj_zip_candidate_rejects_invalid_transfer_control(self):
        ascii_candidate = self._build_ddjj_ascii_candidate_for_zip()

        with self.assertRaisesRegex(ValueError, 'tipo 0'):
            build_annual_tax_ddjj_zip_export_candidate(
                ascii_candidate,
                transfer_control_record={
                    'record': '1' + 'T' * 23,
                    'review_state': 'approved_for_candidate',
                    'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
            )

        with self.assertRaisesRegex(ValueError, 'transfer_source_ref no sensible'):
            build_annual_tax_ddjj_zip_export_candidate(
                ascii_candidate,
                transfer_control_record={
                    'record': '0' + 'T' * 23,
                    'review_state': 'approved_for_candidate',
                    'transfer_source_ref': 'https://sii.example.test/ddjj?token=secret',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
            )

        tampered_candidate = {
            **ascii_candidate,
            'summary': {
                **ascii_candidate['summary'],
                'official_format': True,
            },
        }
        with self.assertRaisesRegex(ValueError, 'candidato oficial'):
            build_annual_tax_ddjj_zip_export_candidate(
                tampered_candidate,
                transfer_control_record={
                    'record': '0' + 'T' * 23,
                    'review_state': 'approved_for_candidate',
                    'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
            )

    def test_tax_export_writes_verifiable_f22_fixed_width_candidate_from_reviewed_codes(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()

        candidate = build_annual_tax_f22_fixed_width_export_candidate(
            export,
            rut_number='11111111',
            rut_dv='1',
            company_code='QA',
            client_number='123456',
            **self._f22_local_certification_kwargs(),
            entries=[
                {
                    'code': '1234',
                    'sign': '+',
                    'value': '1000',
                    'review_state': 'approved_for_candidate',
                    'code_source_ref': 'sii-f22-at2026-code-1234',
                    'value_source_ref': 'lm-rli-reviewed-line-1234',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
                {
                    'code': '2345',
                    'sign': '-',
                    'value': '250',
                    'review_state': 'approved_for_candidate',
                    'code_source_ref': 'sii-f22-at2026-code-2345',
                    'value_source_ref': 'lm-cpt-reviewed-line-2345',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
                {
                    'code': '3456',
                    'value': '0',
                    'review_state': 'approved_for_candidate',
                    'code_source_ref': 'sii-f22-at2026-code-3456',
                    'value_source_ref': 'lm-fiscal-config-reviewed-line-3456',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
                {
                    'code': '4567',
                    'value': '42',
                    'review_state': 'approved_for_candidate',
                    'code_source_ref': 'sii-f22-at2026-code-4567',
                    'value_source_ref': 'lm-ddjj-reviewed-line-4567',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
                {
                    'code': '5678',
                    'value': '900',
                    'review_state': 'approved_for_candidate',
                    'code_source_ref': 'sii-f22-at2026-code-5678',
                    'value_source_ref': 'lm-real-estate-reviewed-line-5678',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
            ],
        )

        summary = candidate['summary']
        records = candidate['records']
        self.assertEqual(summary['candidate_version'], 'annual-tax-f22-fixed-width-candidate-v1')
        self.assertEqual(summary['record_format_version'], 'f22-at2026-fixed-width-record-v1')
        self.assertEqual(summary['record_length'], 90)
        self.assertEqual(summary['records_total'], 3)
        self.assertEqual(summary['type0_records_total'], 1)
        self.assertEqual(summary['type1_records_total'], 2)
        self.assertEqual(summary['f22_codes_total'], 5)
        self.assertEqual(summary['f22_codes'], ['1234', '2345', '3456', '4567', '5678'])
        self.assertEqual(summary['f22_entry_review_evidence_total'], 5)
        self.assertEqual(len(summary['f22_entry_review_evidence']), 5)
        self.assertEqual(summary['f22_entry_review_evidence'][0]['code_source_ref'], 'sii-f22-at2026-code-1234')
        self.assertEqual(summary['f22_entry_review_evidence'][0]['value_source_ref'], 'lm-rli-reviewed-line-1234')
        self.assertEqual(summary['f22_entry_review_evidence'][0]['review_state'], 'approved_for_candidate')
        self.assertIn('entry_hash', summary['f22_entry_review_evidence'][0])
        self.assertTrue(summary['fixed_width_structure_validated'])
        self.assertFalse(summary['official_format'])
        self.assertFalse(summary['sii_submission'])
        self.assertFalse(summary['final_tax_calculation'])
        self.assertEqual(summary['certification_code_review_state'], 'synthetic_for_local_candidate')
        self.assertFalse(summary['certification_code_authorized_by_sii'])
        self.assertFalse(summary['ready_for_certification_submission'])
        certification_evidence = summary['certification_code_evidence']
        self.assertEqual(certification_evidence['review_state'], 'synthetic_for_local_candidate')
        self.assertEqual(
            certification_evidence['certification_code_source_ref'],
            'sii-f22-at2026-cert-code-synthetic-local',
        )
        self.assertFalse(certification_evidence['authorized_by_sii'])
        self.assertIn('company_code_hash', certification_evidence)
        self.assertIn('client_number_hash', certification_evidence)
        self.assertNotIn('company_code', certification_evidence)
        self.assertNotIn('client_number', certification_evidence)
        self.assertEqual(len(records), 3)
        self.assertTrue(all(len(record) == 90 for record in records))
        self.assertEqual(records[0][18:23], '00003')
        self.assertEqual(records[1][1:5], '1234')
        self.assertEqual(records[2][1:5], '5678')

        with TemporaryDirectory() as temp_dir:
            written = write_annual_tax_f22_fixed_width_export_candidate(candidate, temp_dir)
            self.assertTrue(Path(written['written_file']).exists())
            self.assertTrue(Path(written['manifest_file']).exists())
            verification = verify_annual_tax_f22_fixed_width_export_candidate(candidate, temp_dir)

        self.assertTrue(verification['verified'])
        self.assertTrue(verification['ready_for_responsible_review'])
        self.assertEqual(verification['records_total'], 3)
        self.assertEqual(verification['f22_codes_total'], 5)
        self.assertEqual(verification['f22_entry_review_evidence_total'], 5)
        self.assertFalse(verification['official_format'])
        self.assertFalse(verification['sii_submission'])
        self.assertFalse(verification['final_tax_calculation'])
        self.assertEqual(verification['certification_code_review_state'], 'synthetic_for_local_candidate')
        self.assertFalse(verification['certification_code_authorized_by_sii'])
        self.assertTrue(verification['ready_for_certification_review'])
        self.assertFalse(verification['ready_for_certification_submission'])

    def test_tax_export_derives_f22_fixed_width_entries_from_reviewed_mapping_items(self):
        export, mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')

        entries = build_f22_fixed_width_entries_from_artifact_matrix(export)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['code'], '1234')
        self.assertEqual(entries[0]['value'], '1000')
        self.assertEqual(entries[0]['tax_code_mapping_id'], mapping.id)
        self.assertEqual(entries[0]['code_source_ref'], 'sii-f22-at2026-code-1234')
        self.assertEqual(entries[0]['value_source_ref'], 'lm-reviewed-f22-value-1234')

        candidate = build_annual_tax_f22_fixed_width_export_candidate(
            export,
            rut_number='11111111',
            rut_dv='1',
            company_code='QA',
            client_number='123456',
            **self._f22_local_certification_kwargs(),
            entries=entries,
        )

        evidence = candidate['summary']['f22_entry_review_evidence'][0]
        self.assertEqual(candidate['summary']['f22_codes'], ['1234'])
        self.assertEqual(evidence['tax_code_mapping_id'], mapping.id)
        self.assertEqual(evidence['official_source_id'], mapping.official_source_id)
        self.assertEqual(evidence['code_source_ref'], 'sii-f22-at2026-code-1234')

    def test_tax_export_f22_fixed_width_candidate_requires_certification_code_evidence(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        reviewed_entry = {
            'code': '1234',
            'value': '1000',
            'review_state': 'approved_for_candidate',
            'code_source_ref': 'sii-f22-at2026-code-1234',
            'value_source_ref': 'lm-reviewed-line-1234',
            'responsible_review_ref': 'tax-reviewer-at2026-controlled',
        }

        with self.assertRaisesRegex(ValueError, 'certification_code_source_ref'):
            build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                certification_code_source_ref='',
                certification_responsible_review_ref='tax-reviewer-at2026-cert-code-controlled',
                entries=[reviewed_entry],
            )

        with self.assertRaisesRegex(ValueError, 'certification_code_source_ref'):
            build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                certification_code_source_ref='secret://sii-f22-code',
                certification_responsible_review_ref='tax-reviewer-at2026-cert-code-controlled',
                entries=[reviewed_entry],
            )

        with self.assertRaisesRegex(ValueError, 'review_state oficial'):
            build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                **self._f22_local_certification_kwargs(),
                certification_authorized_by_sii=True,
                certification_authorization_ref='sii-f22-at2026-certification-authorization-reviewed',
                entries=[reviewed_entry],
            )

        with self.assertRaisesRegex(ValueError, 'authorization_ref SII'):
            build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                **self._f22_local_certification_kwargs(),
                certification_authorization_ref='sii-f22-at2026-certification-authorization-reviewed',
                entries=[reviewed_entry],
            )

    def test_tax_export_rejects_mapping_entries_without_presentable_f22_code(self):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(
            code='F22-PREVIEW',
            value='1000',
        )

        with self.assertRaisesRegex(ValueError, 'codigo SII numerico de 4 digitos'):
            build_f22_fixed_width_entries_from_artifact_matrix(export)

    def test_tax_export_f22_fixed_width_candidate_rejects_unreviewed_non_numeric_or_duplicate_codes(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()

        with self.assertRaisesRegex(ValueError, 'entradas F22 revisadas'):
            build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                **self._f22_local_certification_kwargs(),
                entries=[],
            )

        with self.assertRaisesRegex(ValueError, 'review_state approved_for_candidate'):
            build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                **self._f22_local_certification_kwargs(),
                entries=[{'code': '1234', 'value': '1000'}],
            )

        with self.assertRaisesRegex(ValueError, 'codigo SII numerico de 4 digitos'):
            build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                **self._f22_local_certification_kwargs(),
                entries=[{'code': 'F22-PREVIEW', 'value': '1000'}],
            )

        reviewed_entry = {
            'code': '1234',
            'value': '1000',
            'review_state': 'approved_for_candidate',
            'code_source_ref': 'sii-f22-at2026-code-1234',
            'value_source_ref': 'lm-reviewed-line-1234',
            'responsible_review_ref': 'tax-reviewer-at2026-controlled',
        }
        with self.assertRaisesRegex(ValueError, 'codigos F22 duplicados'):
            build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                **self._f22_local_certification_kwargs(),
                entries=[reviewed_entry, reviewed_entry],
            )

        with self.assertRaisesRegex(ValueError, 'referencias no sensibles'):
            build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                **self._f22_local_certification_kwargs(),
                entries=[
                    {
                        **reviewed_entry,
                        'code': '2345',
                        'value_source_ref': 'secret://f22-value-source',
                    }
                ],
            )

    def test_tax_export_f22_fixed_width_candidate_manifest_tamper_is_rejected(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        candidate = build_annual_tax_f22_fixed_width_export_candidate(
            export,
            rut_number='11111111',
            rut_dv='1',
            company_code='QA',
            client_number='123456',
            **self._f22_local_certification_kwargs(),
            entries=[
                {
                    'code': '1234',
                    'value': '1000',
                    'review_state': 'approved_for_candidate',
                    'code_source_ref': 'sii-f22-at2026-code-1234',
                    'value_source_ref': 'lm-reviewed-line-1234',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                }
            ],
        )

        with TemporaryDirectory() as temp_dir:
            written = write_annual_tax_f22_fixed_width_export_candidate(candidate, temp_dir)
            manifest_path = Path(written['manifest_file'])
            manifest_payload = json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest_payload['summary']['ready_for_certification_submission'] = True
            manifest_path.write_text(
                json.dumps(manifest_payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True),
                encoding='utf-8',
            )

            with self.assertRaisesRegex(ValueError, 'no coincide con el candidato esperado'):
                verify_annual_tax_f22_fixed_width_export_candidate(candidate, temp_dir)

        tampered_candidate = {
            **candidate,
            'summary': {
                **candidate['summary'],
                'ready_for_certification_submission': True,
            },
        }
        with TemporaryDirectory() as temp_dir:
            write_annual_tax_f22_fixed_width_export_candidate(tampered_candidate, temp_dir)
            with self.assertRaisesRegex(ValueError, 'no puede declararse listo'):
                verify_annual_tax_f22_fixed_width_export_candidate(tampered_candidate, temp_dir)

        raw_value_evidence = {
            **candidate['summary']['certification_code_evidence'],
            'company_code': 'QA',
            'client_number': '123456',
        }
        raw_value_evidence['evidence_hash'] = hashlib.sha256(
            json.dumps(
                {key: value for key, value in raw_value_evidence.items() if key != 'evidence_hash'},
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
            ).encode('utf-8')
        ).hexdigest()
        raw_value_candidate = {
            **candidate,
            'summary': {
                **candidate['summary'],
                'certification_code_evidence': raw_value_evidence,
                'certification_code_evidence_hash': hashlib.sha256(
                    json.dumps(
                        raw_value_evidence,
                        sort_keys=True,
                        separators=(',', ':'),
                        ensure_ascii=True,
                    ).encode('utf-8')
                ).hexdigest(),
            },
        }
        with TemporaryDirectory() as temp_dir:
            write_annual_tax_f22_fixed_width_export_candidate(raw_value_candidate, temp_dir)
            with self.assertRaisesRegex(ValueError, 'valores crudos'):
                verify_annual_tax_f22_fixed_width_export_candidate(raw_value_candidate, temp_dir)

    def test_tax_export_written_package_tamper_is_rejected(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()

        with TemporaryDirectory() as temp_dir:
            written = write_annual_tax_export_file_package(export, temp_dir)
            tampered_path = Path(written['written_files'][0])
            tampered_payload = json.loads(tampered_path.read_text(encoding='utf-8'))
            tampered_payload['target_code'] = 'F22-TAMPERED'
            tampered_path.write_text(
                json.dumps(tampered_payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True),
                encoding='utf-8',
            )

            with self.assertRaisesRegex(ValueError, 'hash/tamano esperado'):
                verify_annual_tax_export_file_package(export, temp_dir)

    def test_tax_export_written_package_noncanonical_manifest_is_rejected(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()

        with TemporaryDirectory() as temp_dir:
            written = write_annual_tax_export_file_package(export, temp_dir)
            manifest_path = Path(written['manifest_file'])
            manifest_payload = json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding='utf-8')

            with self.assertRaisesRegex(ValueError, 'JSON canonico'):
                verify_annual_tax_export_file_package(export, temp_dir)

    def test_tax_export_written_package_extra_entry_is_rejected(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()

        with TemporaryDirectory() as temp_dir:
            write_annual_tax_export_file_package(export, temp_dir)
            (Path(temp_dir) / 'extra').mkdir()

            with self.assertRaisesRegex(ValueError, 'entradas no permitidas'):
                verify_annual_tax_export_file_package(export, temp_dir)

    def test_materialize_annual_tax_export_file_package_command_writes_verified_local_package(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            output_dir = Path(temp_dir) / 'annual-export-package'
            stdout = StringIO()

            call_command(
                'materialize_annual_tax_export_file_package',
                export_id=export.pk,
                output_dir=str(output_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            verification = verify_annual_tax_export_file_package(export, output_dir)

            self.assertTrue(result['materialized'])
            self.assertEqual(result['annual_tax_export_id'], export.pk)
            self.assertEqual(result['files_total'], export.target_items_total)
            self.assertEqual(result['package_hash'], verification['package_hash'])
            self.assertEqual(result['verification']['package_hash'], verification['package_hash'])
            self.assertEqual(
                sorted(result['written_files']),
                sorted(file_result['file_name'] for file_result in verification['file_results']),
            )
            self.assertTrue((output_dir / 'manifest.json').is_file())
            self.assertEqual(len(result['written_files']), verification['files_total'])
            self.assertFalse(result['official_format'])
            self.assertFalse(result['sii_submission'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertTrue(result['ready_for_responsible_review'])
            self.assertTrue(result['requires_official_format_gate'])
            self.assertTrue(result['requires_explicit_submission_authorization'])

    def test_materialize_annual_tax_export_file_package_rejects_nonempty_output_dir(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            output_dir = Path(temp_dir) / 'annual-export-package'
            output_dir.mkdir()
            stale_file = output_dir / 'stale.txt'
            stale_file.write_text('previous export residue', encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'debe estar vacio'):
                call_command(
                    'materialize_annual_tax_export_file_package',
                    export_id=export.pk,
                    output_dir=str(output_dir),
                    stdout=StringIO(),
                )

            self.assertEqual(stale_file.read_text(encoding='utf-8'), 'previous export residue')
            self.assertFalse((output_dir / 'manifest.json').exists())

    def test_materialize_annual_tax_export_file_package_rejects_versioned_repo_output(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage6-export-package-should-not-be-versioned'

        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'materialize_annual_tax_export_file_package',
                export_id=export.pk,
                output_dir=str(blocked_output),
                stdout=StringIO(),
            )
        self.assertFalse(blocked_output.exists())

    def test_materialize_annual_tax_f22_fixed_width_candidate_command_writes_verified_local_file(self):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            output_dir = Path(temp_dir) / 'f22-fixed-width-candidate'
            stdout = StringIO()

            call_command(
                'materialize_annual_tax_f22_fixed_width_candidate',
                export_id=export.pk,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                output_dir=str(output_dir),
                stdout=stdout,
                **self._f22_local_certification_kwargs(),
            )

            result = json.loads(stdout.getvalue())
            entries = build_f22_fixed_width_entries_from_artifact_matrix(export)
            candidate = build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                **self._f22_local_certification_kwargs(),
                entries=entries,
            )
            verification = verify_annual_tax_f22_fixed_width_export_candidate(candidate, output_dir)

            self.assertTrue(result['materialized'])
            self.assertEqual(result['annual_tax_export_id'], export.pk)
            self.assertEqual(result['candidate_version'], 'annual-tax-f22-fixed-width-candidate-v1')
            self.assertEqual(result['record_format_version'], 'f22-at2026-fixed-width-record-v1')
            self.assertEqual(result['records_total'], verification['records_total'])
            self.assertEqual(result['f22_codes_total'], 1)
            self.assertEqual(result['f22_entry_review_evidence_total'], 1)
            self.assertEqual(result['content_hash'], verification['content_hash'])
            self.assertEqual(result['certification_code_review_state'], 'synthetic_for_local_candidate')
            self.assertFalse(result['certification_code_authorized_by_sii'])
            self.assertFalse(result['official_format'])
            self.assertFalse(result['sii_submission'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertTrue(result['ready_for_responsible_review'])
            self.assertTrue(result['ready_for_certification_review'])
            self.assertFalse(result['ready_for_certification_submission'])
            self.assertTrue(result['requires_explicit_submission_authorization'])
            self.assertTrue((output_dir / result['written_file']).is_file())
            self.assertTrue((output_dir / result['manifest_file']).is_file())
            rendered = stdout.getvalue()
            self.assertNotIn('11111111', rendered)
            self.assertNotIn('QA', rendered)
            self.assertNotIn('123456', rendered)
            self.assertIn('company_code_hash', result)
            self.assertIn('client_number_hash', result)

    def test_materialize_annual_tax_f22_fixed_width_candidate_rejects_nonempty_output_dir(self):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            output_dir = Path(temp_dir) / 'f22-fixed-width-candidate'
            output_dir.mkdir()
            stale_file = output_dir / 'stale.txt'
            stale_file.write_text('previous f22 residue', encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'debe estar vacio'):
                call_command(
                    'materialize_annual_tax_f22_fixed_width_candidate',
                    export_id=export.pk,
                    rut_number='11111111',
                    rut_dv='1',
                    company_code='QA',
                    client_number='123456',
                    output_dir=str(output_dir),
                    stdout=StringIO(),
                    **self._f22_local_certification_kwargs(),
                )

            self.assertEqual(stale_file.read_text(encoding='utf-8'), 'previous f22 residue')
            self.assertFalse((output_dir / 'f22-fixed-width-candidate-manifest.json').exists())

    def test_materialize_annual_tax_f22_fixed_width_candidate_rejects_versioned_repo_output(self):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage6-f22-candidate-should-not-be-versioned'

        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'materialize_annual_tax_f22_fixed_width_candidate',
                export_id=export.pk,
                rut_number='11111111',
                rut_dv='1',
                company_code='QA',
                client_number='123456',
                output_dir=str(blocked_output),
                stdout=StringIO(),
                **self._f22_local_certification_kwargs(),
            )
        self.assertFalse(blocked_output.exists())

    def test_materialize_annual_tax_ddjj_ascii_candidate_command_writes_verified_local_file(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        records = self._ddjj_ascii_records(ddjj_item)
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            output_dir = Path(temp_dir) / 'ddjj-ascii-candidate'
            stdout = StringIO()

            call_command(
                'materialize_annual_tax_ddjj_ascii_candidate',
                export_id=export.pk,
                form_code='1887',
                rut_number='97030000',
                records_json=json.dumps(records),
                output_dir=str(output_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            candidate = build_annual_tax_ddjj_ascii_export_candidate(
                export,
                form_code='1887',
                rut_number='97030000',
                records=records,
            )
            verification = verify_annual_tax_ddjj_ascii_export_candidate(candidate, output_dir)

            self.assertTrue(result['materialized'])
            self.assertEqual(result['annual_tax_export_id'], export.pk)
            self.assertEqual(result['candidate_version'], 'annual-tax-ddjj-ascii-candidate-v1')
            self.assertEqual(result['record_format_version'], 'ddjj-at2026-ascii-positional-candidate-v1')
            self.assertEqual(result['form_code'], '1887')
            self.assertEqual(result['file_extension'], '887')
            self.assertEqual(result['file_name_hash'], hashlib.sha256(b'97030000.887').hexdigest())
            self.assertEqual(result['records_total'], verification['records_total'])
            self.assertEqual(result['record_length'], verification['record_length'])
            self.assertEqual(result['record_type_counts'], {'1': 1, '2': 1, '3': 1})
            self.assertEqual(result['ddjj_record_review_evidence_total'], 3)
            self.assertEqual(result['content_hash'], verification['content_hash'])
            self.assertFalse(result['official_format'])
            self.assertFalse(result['sii_submission'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertTrue(result['ready_for_responsible_review'])
            self.assertTrue(result['requires_exact_form_layout_gate'])
            self.assertTrue(result['requires_explicit_submission_authorization'])
            self.assertTrue((output_dir / '97030000.887').is_file())
            self.assertTrue((output_dir / result['manifest_file']).is_file())
            rendered = stdout.getvalue()
            self.assertNotIn('97030000', rendered)
            self.assertNotIn('AAAAAAAAAAAAAAAAAAAAAAA', rendered)
            self.assertNotIn('BBBBBBBBBBBBBBBBBBBBBBB', rendered)
            self.assertNotIn('CCCCCCCCCCCCCCCCCCCCCCC', rendered)

    def test_materialize_annual_tax_ddjj_zip_candidate_command_writes_verified_local_zip(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        records = self._ddjj_ascii_records(ddjj_item)
        transfer_control_record = {
            'record': '0' + 'T' * 23,
            'review_state': 'approved_for_candidate',
            'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
            'responsible_review_ref': 'tax-reviewer-at2026-controlled',
        }
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            output_dir = Path(temp_dir) / 'ddjj-zip-candidate'
            stdout = StringIO()

            call_command(
                'materialize_annual_tax_ddjj_zip_candidate',
                export_id=export.pk,
                form_code='1887',
                rut_number='97030000',
                records_json=json.dumps(records),
                transfer_control_json=json.dumps(transfer_control_record),
                output_dir=str(output_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            ascii_candidate = build_annual_tax_ddjj_ascii_export_candidate(
                export,
                form_code='1887',
                rut_number='97030000',
                records=records,
            )
            zip_candidate = build_annual_tax_ddjj_zip_export_candidate(
                ascii_candidate,
                transfer_control_record=transfer_control_record,
            )
            verification = verify_annual_tax_ddjj_zip_export_candidate(zip_candidate, output_dir)

            self.assertTrue(result['materialized'])
            self.assertEqual(result['annual_tax_export_id'], export.pk)
            self.assertEqual(result['candidate_version'], 'annual-tax-ddjj-zip-candidate-v1')
            self.assertEqual(result['source_candidate_version'], 'annual-tax-ddjj-ascii-candidate-v1')
            self.assertEqual(result['record_format_version'], 'ddjj-at2026-transfer-zip-candidate-v1')
            self.assertEqual(result['form_code'], '1887')
            self.assertEqual(result['zip_file_name_hash'], hashlib.sha256(b'97030000.887.zip').hexdigest())
            self.assertEqual(result['zip_file_hash'], verification['zip_file_hash'])
            self.assertEqual(result['records_total'], verification['records_total'])
            self.assertEqual(result['record_length'], verification['record_length'])
            self.assertEqual(result['record_type_counts'], {'0': 1, '1': 1, '2': 1, '3': 1})
            self.assertEqual(result['content_hash'], verification['content_hash'])
            self.assertFalse(result['official_format'])
            self.assertFalse(result['sii_submission'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertTrue(result['ready_for_responsible_review'])
            self.assertFalse(result['ready_for_submission'])
            self.assertTrue(result['requires_official_zip_gate'])
            self.assertTrue(result['requires_explicit_submission_authorization'])
            self.assertTrue((output_dir / '97030000.887.zip').is_file())
            self.assertTrue((output_dir / result['manifest_file']).is_file())
            rendered = stdout.getvalue()
            self.assertNotIn('97030000', rendered)
            self.assertNotIn('AAAAAAAAAAAAAAAAAAAAAAA', rendered)
            self.assertNotIn('TTTTTTTTTTTTTTTTTTTTTTT', rendered)

    def test_presentation_review_bundle_allows_controlled_approval_only_when_official_compatibility_is_ready(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            inputs = self._materialize_presentation_review_inputs(temp_dir)
            export = inputs['export']
            checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
            register_annual_tax_review_decision(
                checklist,
                review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
                decision_ref='annual-tax-manual-approval-at2026-controlled',
                decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
                responsible_ref='tax-reviewer-final-approval-controlled',
                reason='manual_review_completed_for_controlled_bundle',
            )

            bundle = build_annual_tax_presentation_review_bundle(
                export,
                export_package_dir=inputs['export_package_dir'],
                f22_candidate_dir=inputs['f22_dir'],
                ddjj_ascii_candidate_dirs=[inputs['ddjj_ascii_dir']],
                ddjj_zip_candidate_dirs=[inputs['ddjj_zip_dir']],
            )

            self.assertEqual(bundle['summary']['classification'], 'aprobado_para_presentacion_controlada')
            self.assertTrue(bundle['summary']['ready_for_controlled_presentation_review'])
            self.assertTrue(bundle['summary']['artifact_coverage_ready'])
            self.assertEqual(bundle['summary']['artifact_coverage_issue_codes'], [])
            self.assertTrue(bundle['artifact_coverage']['ready_for_presentation_artifact_coverage'])
            self.assertEqual(bundle['artifact_coverage']['expected_ddjj_forms_total'], 1)
            self.assertEqual(bundle['artifact_coverage']['provided_ddjj_ascii_forms'], ['1887'])
            self.assertEqual(bundle['artifact_coverage']['provided_ddjj_zip_forms'], ['1887'])
            self.assertTrue(bundle['summary']['official_compatibility_ready'])
            self.assertEqual(bundle['summary']['official_compatibility_blocking_gap_keys'], [])
            self.assertEqual(bundle['issues'], [])
            self.assertFalse(bundle['boundary']['ready_for_sii_submission'])
            self.assertFalse(bundle['summary']['official_format'])
            self.assertFalse(bundle['summary']['sii_submission'])
            self.assertFalse(bundle['summary']['final_tax_calculation'])

    def test_presentation_review_bundle_blocks_controlled_approval_when_official_compatibility_has_gap(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            inputs = self._materialize_presentation_review_inputs(temp_dir)
            export = inputs['export']
            checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
            register_annual_tax_review_decision(
                checklist,
                review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
                decision_ref='annual-tax-manual-approval-at2026-controlled',
                decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
                responsible_ref='tax-reviewer-final-approval-controlled',
                reason='manual_review_completed_with_official_gap_for_test',
            )
            compatibility_gap = {
                'schema_version': 'stage6-official-presentation-compatibility-summary-v1',
                'matrix_schema_version': 'stage6-official-compatibility-at2025-at2026-v1',
                'anio_tributario': export.anio_tributario,
                'supported_tax_years': [2025, 2026],
                'verified_on': '2026-06-18',
                'issue_codes': [],
                'known_gap_keys': ['f22_record_format_2025'],
                'blocking_gap_keys': ['f22_record_format_2025'],
                'ready_for_controlled_presentation_approval': False,
                'official_submission_allowed': False,
                'public_api_general_available': False,
                'final_tax_calculation': False,
                'requires_responsible_review': True,
            }

            with patch(
                'sii.services.summarize_stage6_official_compatibility_for_presentation',
                return_value=compatibility_gap,
            ):
                bundle = build_annual_tax_presentation_review_bundle(
                    export,
                    export_package_dir=inputs['export_package_dir'],
                    f22_candidate_dir=inputs['f22_dir'],
                    ddjj_ascii_candidate_dirs=[inputs['ddjj_ascii_dir']],
                    ddjj_zip_candidate_dirs=[inputs['ddjj_zip_dir']],
                )

            self.assertEqual(bundle['summary']['classification'], 'preparado_con_brecha_oficial')
            self.assertFalse(bundle['summary']['ready_for_controlled_presentation_review'])
            self.assertFalse(bundle['summary']['official_compatibility_ready'])
            self.assertEqual(bundle['summary']['official_compatibility_blocking_gap_keys'], ['f22_record_format_2025'])
            self.assertIn(
                'stage6.presentation_review.official_compatibility_gap',
                {issue['code'] for issue in bundle['issues']},
            )
            self.assertTrue(bundle['boundary']['requires_responsible_review'])
            self.assertFalse(bundle['boundary']['ready_for_sii_submission'])

    def test_presentation_review_bundle_blocks_controlled_approval_when_f22_candidate_is_missing(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            inputs = self._materialize_presentation_review_inputs(temp_dir)
            export = inputs['export']
            checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
            register_annual_tax_review_decision(
                checklist,
                review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
                decision_ref='annual-tax-manual-approval-at2026-controlled',
                decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
                responsible_ref='tax-reviewer-final-approval-controlled',
                reason='manual_review_completed_but_f22_candidate_missing',
            )

            bundle = build_annual_tax_presentation_review_bundle(
                export,
                export_package_dir=inputs['export_package_dir'],
                ddjj_ascii_candidate_dirs=[inputs['ddjj_ascii_dir']],
                ddjj_zip_candidate_dirs=[inputs['ddjj_zip_dir']],
            )

            self.assertEqual(bundle['summary']['classification'], 'preparado_con_cobertura_incompleta')
            self.assertFalse(bundle['summary']['ready_for_controlled_presentation_review'])
            self.assertFalse(bundle['summary']['artifact_coverage_ready'])
            self.assertIn(
                'stage6.presentation_artifact_coverage.f22_candidate_missing',
                bundle['summary']['artifact_coverage_issue_codes'],
            )
            self.assertIn(
                'stage6.presentation_review.artifact_coverage_gap',
                {issue['code'] for issue in bundle['issues']},
            )
            self.assertTrue(bundle['summary']['official_compatibility_ready'])
            self.assertTrue(bundle['boundary']['requires_responsible_review'])
            self.assertFalse(bundle['boundary']['ready_for_sii_submission'])

    def test_presentation_review_bundle_blocks_controlled_approval_when_ddjj_zip_is_missing(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            inputs = self._materialize_presentation_review_inputs(temp_dir)
            export = inputs['export']
            checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
            register_annual_tax_review_decision(
                checklist,
                review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
                decision_ref='annual-tax-manual-approval-at2026-controlled',
                decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
                responsible_ref='tax-reviewer-final-approval-controlled',
                reason='manual_review_completed_but_ddjj_zip_missing',
            )

            bundle = build_annual_tax_presentation_review_bundle(
                export,
                export_package_dir=inputs['export_package_dir'],
                f22_candidate_dir=inputs['f22_dir'],
                ddjj_ascii_candidate_dirs=[inputs['ddjj_ascii_dir']],
            )

            self.assertEqual(bundle['summary']['classification'], 'preparado_con_cobertura_incompleta')
            self.assertFalse(bundle['summary']['ready_for_controlled_presentation_review'])
            self.assertFalse(bundle['summary']['artifact_coverage_ready'])
            self.assertIn(
                'stage6.presentation_artifact_coverage.ddjj_zip_missing',
                bundle['summary']['artifact_coverage_issue_codes'],
            )
            self.assertIn(
                'stage6.presentation_review.artifact_coverage_gap',
                {issue['code'] for issue in bundle['issues']},
            )
            self.assertTrue(bundle['summary']['official_compatibility_ready'])
            self.assertTrue(bundle['boundary']['requires_responsible_review'])
            self.assertFalse(bundle['boundary']['ready_for_sii_submission'])

    def test_presentation_review_bundle_blocks_controlled_approval_when_ddjj_candidate_is_unexpected(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            inputs = self._materialize_presentation_review_inputs(temp_dir)
            unexpected_ascii_dir = Path(temp_dir) / 'ddjj-ascii-unexpected-candidate'
            unexpected_ascii_dir.mkdir()
            for source_path in inputs['ddjj_ascii_dir'].iterdir():
                if source_path.is_file():
                    (unexpected_ascii_dir / source_path.name).write_bytes(source_path.read_bytes())
            manifest_path = unexpected_ascii_dir / 'ddjj-ascii-candidate-manifest.json'
            manifest_payload = json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest_payload['summary']['form_code'] = '9999'
            manifest_path.write_text(
                json.dumps(
                    manifest_payload,
                    sort_keys=True,
                    separators=(',', ':'),
                    ensure_ascii=True,
                    default=str,
                ),
                encoding='utf-8',
            )
            export = inputs['export']
            checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
            register_annual_tax_review_decision(
                checklist,
                review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
                decision_ref='annual-tax-manual-approval-at2026-controlled',
                decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
                responsible_ref='tax-reviewer-final-approval-controlled',
                reason='manual_review_completed_but_ddjj_candidate_unexpected',
            )

            bundle = build_annual_tax_presentation_review_bundle(
                export,
                export_package_dir=inputs['export_package_dir'],
                f22_candidate_dir=inputs['f22_dir'],
                ddjj_ascii_candidate_dirs=[inputs['ddjj_ascii_dir'], unexpected_ascii_dir],
                ddjj_zip_candidate_dirs=[inputs['ddjj_zip_dir']],
            )

            self.assertEqual(bundle['summary']['classification'], 'preparado_con_cobertura_incompleta')
            self.assertFalse(bundle['summary']['artifact_coverage_ready'])
            self.assertEqual(bundle['artifact_coverage']['unexpected_ddjj_ascii_forms'], ['9999'])
            self.assertIn(
                'stage6.presentation_artifact_coverage.ddjj_ascii_unexpected_form',
                bundle['summary']['artifact_coverage_issue_codes'],
            )
            self.assertIn(
                'stage6.presentation_review.artifact_coverage_gap',
                {issue['code'] for issue in bundle['issues']},
            )

    def test_presentation_review_bundle_blocks_controlled_approval_when_ddjj_ascii_candidate_is_duplicated(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            inputs = self._materialize_presentation_review_inputs(temp_dir)
            export = inputs['export']
            checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
            register_annual_tax_review_decision(
                checklist,
                review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
                decision_ref='annual-tax-manual-approval-at2026-controlled',
                decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
                responsible_ref='tax-reviewer-final-approval-controlled',
                reason='manual_review_completed_but_ddjj_ascii_candidate_duplicated',
            )

            bundle = build_annual_tax_presentation_review_bundle(
                export,
                export_package_dir=inputs['export_package_dir'],
                f22_candidate_dir=inputs['f22_dir'],
                ddjj_ascii_candidate_dirs=[inputs['ddjj_ascii_dir'], inputs['ddjj_ascii_dir']],
                ddjj_zip_candidate_dirs=[inputs['ddjj_zip_dir']],
            )

            self.assertEqual(bundle['summary']['classification'], 'preparado_con_cobertura_incompleta')
            self.assertFalse(bundle['summary']['artifact_coverage_ready'])
            self.assertIn(
                'stage6.presentation_artifact_coverage.ddjj_ascii_duplicate',
                bundle['summary']['artifact_coverage_issue_codes'],
            )
            self.assertIn(
                'stage6.presentation_review.artifact_coverage_gap',
                {issue['code'] for issue in bundle['issues']},
            )

    def test_materialize_annual_tax_ddjj_candidate_commands_reject_nonempty_output_dirs(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        records = self._ddjj_ascii_records(ddjj_item)
        transfer_control_record = {
            'record': '0' + 'T' * 23,
            'review_state': 'approved_for_candidate',
            'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
            'responsible_review_ref': 'tax-reviewer-at2026-controlled',
        }
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        command_cases = (
            (
                'materialize_annual_tax_ddjj_ascii_candidate',
                {'records_json': json.dumps(records)},
                'ddjj-ascii-candidate-manifest.json',
            ),
            (
                'materialize_annual_tax_ddjj_zip_candidate',
                {
                    'records_json': json.dumps(records),
                    'transfer_control_json': json.dumps(transfer_control_record),
                },
                'ddjj-zip-candidate-manifest.json',
            ),
        )

        for command_name, extra_options, manifest_name in command_cases:
            with self.subTest(command=command_name), TemporaryDirectory(dir=local_evidence_root) as temp_dir:
                output_dir = Path(temp_dir) / 'ddjj-candidate'
                output_dir.mkdir()
                stale_file = output_dir / 'stale.txt'
                stale_file.write_text('previous ddjj residue', encoding='utf-8')

                with self.assertRaisesMessage(CommandError, 'debe estar vacio'):
                    call_command(
                        command_name,
                        export_id=export.pk,
                        form_code='1887',
                        rut_number='97030000',
                        output_dir=str(output_dir),
                        stdout=StringIO(),
                        **extra_options,
                    )

                self.assertEqual(stale_file.read_text(encoding='utf-8'), 'previous ddjj residue')
                self.assertFalse((output_dir / manifest_name).exists())

    def test_materialize_annual_tax_ddjj_candidate_commands_reject_versioned_repo_output(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        records = self._ddjj_ascii_records(ddjj_item)
        transfer_control_record = {
            'record': '0' + 'T' * 23,
            'review_state': 'approved_for_candidate',
            'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
            'responsible_review_ref': 'tax-reviewer-at2026-controlled',
        }
        command_cases = (
            (
                'materialize_annual_tax_ddjj_ascii_candidate',
                {'records_json': json.dumps(records)},
                'stage6-ddjj-ascii-candidate-should-not-be-versioned',
            ),
            (
                'materialize_annual_tax_ddjj_zip_candidate',
                {
                    'records_json': json.dumps(records),
                    'transfer_control_json': json.dumps(transfer_control_record),
                },
                'stage6-ddjj-zip-candidate-should-not-be-versioned',
            ),
        )

        for command_name, extra_options, output_name in command_cases:
            blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / output_name
            with self.subTest(command=command_name), self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    command_name,
                    export_id=export.pk,
                    form_code='1887',
                    rut_number='97030000',
                    output_dir=str(blocked_output),
                    stdout=StringIO(),
                    **extra_options,
                )
            self.assertFalse(blocked_output.exists())

    def test_materialize_annual_tax_presentation_review_bundle_command_writes_verified_bundle(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            inputs = self._materialize_presentation_review_inputs(temp_dir)
            export = inputs['export']
            output_dir = Path(temp_dir) / 'presentation-review-bundle'
            stdout = StringIO()

            call_command(
                'materialize_annual_tax_presentation_review_bundle',
                export_id=export.pk,
                export_package_dir=str(inputs['export_package_dir']),
                f22_candidate_dir=str(inputs['f22_dir']),
                ddjj_ascii_candidate_dir=[str(inputs['ddjj_ascii_dir'])],
                ddjj_zip_candidate_dir=[str(inputs['ddjj_zip_dir'])],
                output_dir=str(output_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            verification = verify_annual_tax_presentation_review_bundle(
                export,
                output_dir,
                export_package_dir=inputs['export_package_dir'],
                f22_candidate_dir=inputs['f22_dir'],
                ddjj_ascii_candidate_dirs=[inputs['ddjj_ascii_dir']],
                ddjj_zip_candidate_dirs=[inputs['ddjj_zip_dir']],
            )
            bundle = build_annual_tax_presentation_review_bundle(
                export,
                export_package_dir=inputs['export_package_dir'],
                f22_candidate_dir=inputs['f22_dir'],
                ddjj_ascii_candidate_dirs=[inputs['ddjj_ascii_dir']],
                ddjj_zip_candidate_dirs=[inputs['ddjj_zip_dir']],
            )

            self.assertTrue(result['materialized'])
            self.assertEqual(result['annual_tax_export_id'], export.pk)
            self.assertEqual(result['bundle_version'], 'annual-tax-presentation-review-bundle-v1')
            self.assertEqual(result['bundle_hash'], verification['bundle_hash'])
            self.assertEqual(result['bundle_hash'], bundle['summary']['bundle_hash'])
            self.assertEqual(result['classification'], 'preparado_para_revision')
            self.assertEqual(result['artifacts_total'], 4)
            self.assertEqual(result['artifacts_verified_total'], 4)
            self.assertTrue(result['verification']['artifact_coverage_ready'])
            self.assertEqual(result['verification']['artifact_coverage_issue_codes'], [])
            self.assertEqual(
                result['artifact_kinds'],
                [
                    'annual_tax_export_file_package',
                    'ddjj_ascii_candidate',
                    'ddjj_zip_candidate',
                    'f22_fixed_width_candidate',
                ],
            )
            self.assertEqual(result['review_decision_state'], 'preparado')
            self.assertFalse(result['ready_for_controlled_presentation_review'])
            self.assertFalse(result['ready_for_sii_submission'])
            self.assertFalse(result['official_format'])
            self.assertFalse(result['sii_submission'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertTrue(result['requires_official_format_gate'])
            self.assertTrue(result['requires_explicit_submission_authorization'])
            self.assertTrue((output_dir / result['manifest_file']).is_file())

            rendered = stdout.getvalue()
            bundle_rendered = (output_dir / result['manifest_file']).read_text(encoding='utf-8')
            for sensitive_value in (
                '97030000',
                '97030000.887',
                '11111111',
                'QA',
                '123456',
                'AAAAAAAAAAAAAAAAAAAAAAA',
                'BBBBBBBBBBBBBBBBBBBBBBB',
                'CCCCCCCCCCCCCCCCCCCCCCC',
                'TTTTTTTTTTTTTTTTTTTTTTT',
            ):
                self.assertNotIn(sensitive_value, rendered)
                self.assertNotIn(sensitive_value, bundle_rendered)

    def test_materialize_annual_tax_controlled_presentation_package_command_writes_verified_package(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
            process = ProcesoRentaAnual.objects.get()
            rule_set = TaxYearRuleSet.objects.get()
            source_bundle = AnnualTaxSourceBundle.objects.get()
            sync_annual_tax_review_checklist(process, rule_set, source_bundle)
            export.refresh_from_db()
            checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
            register_annual_tax_review_decision(
                checklist,
                review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
                decision_ref='annual-tax-manual-approval-at2026-controlled',
                decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
                responsible_ref='tax-reviewer-final-approval-controlled',
                reason='manual_review_completed_for_controlled_package',
            )
            ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
            self.assertIsNotNone(ddjj_item)
            ddjj_inputs = {
                '1887': {
                    'records': self._ddjj_ascii_records(ddjj_item),
                    'transfer_control_record': {
                        'record': '0' + 'T' * 23,
                        'review_state': 'approved_for_candidate',
                        'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                        'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                    },
                }
            }
            output_dir = Path(temp_dir) / 'controlled-presentation-package'
            stdout = StringIO()

            call_command(
                'materialize_annual_tax_controlled_presentation_package',
                export_id=export.pk,
                rut_number='97030000',
                rut_dv='0',
                company_code='QA',
                client_number='123456',
                ddjj_inputs_json=json.dumps(ddjj_inputs),
                output_dir=str(output_dir),
                handoff_authorization_ref='annual-tax-controlled-handoff-authorization-at2026',
                responsible_ref='tax-reviewer-controlled-handoff-at2026',
                presentation_window_ref='presentation-window-at2026-controlled-local',
                package_note='controlled_handoff_without_sii_submission',
                stdout=stdout,
                **self._f22_local_certification_kwargs(),
            )

            result = json.loads(stdout.getvalue())
            export_package_dir = output_dir / 'annual-tax-export-package'
            f22_dir = output_dir / 'f22-fixed-width-candidate'
            ddjj_ascii_dir = output_dir / 'ddjj-1887-ascii-candidate'
            ddjj_zip_dir = output_dir / 'ddjj-1887-zip-candidate'
            bundle_dir = output_dir / 'presentation-review-bundle'
            controlled_package_dir = output_dir / 'controlled-presentation-handoff'
            export_verification = verify_annual_tax_export_file_package(export, export_package_dir)
            f22_entries = build_f22_fixed_width_entries_from_artifact_matrix(export)
            f22_candidate = build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number='97030000',
                rut_dv='0',
                company_code='QA',
                client_number='123456',
                entries=f22_entries,
                **self._f22_local_certification_kwargs(),
            )
            f22_verification = verify_annual_tax_f22_fixed_width_export_candidate(f22_candidate, f22_dir)
            ascii_candidate = build_annual_tax_ddjj_ascii_export_candidate(
                export,
                form_code='1887',
                rut_number='97030000',
                records=ddjj_inputs['1887']['records'],
            )
            ascii_verification = verify_annual_tax_ddjj_ascii_export_candidate(ascii_candidate, ddjj_ascii_dir)
            zip_candidate = build_annual_tax_ddjj_zip_export_candidate(
                ascii_candidate,
                transfer_control_record=ddjj_inputs['1887']['transfer_control_record'],
            )
            zip_verification = verify_annual_tax_ddjj_zip_export_candidate(zip_candidate, ddjj_zip_dir)
            bundle_verification = verify_annual_tax_presentation_review_bundle(
                export,
                bundle_dir,
                export_package_dir=export_package_dir,
                f22_candidate_dir=f22_dir,
                ddjj_ascii_candidate_dirs=[ddjj_ascii_dir],
                ddjj_zip_candidate_dirs=[ddjj_zip_dir],
            )
            controlled_verification = verify_annual_tax_controlled_presentation_package(
                export,
                controlled_package_dir,
                presentation_review_bundle_dir=bundle_dir,
                export_package_dir=export_package_dir,
                f22_candidate_dir=f22_dir,
                ddjj_ascii_candidate_dirs=[ddjj_ascii_dir],
                ddjj_zip_candidate_dirs=[ddjj_zip_dir],
                handoff_authorization_ref='annual-tax-controlled-handoff-authorization-at2026',
                responsible_ref='tax-reviewer-controlled-handoff-at2026',
                presentation_window_ref='presentation-window-at2026-controlled-local',
                package_note='controlled_handoff_without_sii_submission',
            )

            self.assertTrue(result['materialized'])
            self.assertEqual(result['annual_tax_export_id'], export.pk)
            self.assertEqual(result['export_package_hash'], export_verification['package_hash'])
            self.assertEqual(result['f22_content_hash'], f22_verification['content_hash'])
            self.assertEqual(result['f22_codes_total'], 1)
            self.assertEqual(result['company_code_hash'], hashlib.sha256(b'QA').hexdigest())
            self.assertEqual(result['client_number_hash'], hashlib.sha256(b'123456').hexdigest())
            self.assertEqual(result['ddjj_forms'], ['1887'])
            self.assertEqual(result['ddjj_results'][0]['ascii_content_hash'], ascii_verification['content_hash'])
            self.assertEqual(result['ddjj_results'][0]['zip_file_hash'], zip_verification['zip_file_hash'])
            self.assertEqual(result['presentation_bundle_hash'], bundle_verification['bundle_hash'])
            self.assertEqual(result['controlled_package_hash'], controlled_verification['package_hash'])
            self.assertEqual(result['classification'], 'preparado_para_presentacion_controlada')
            self.assertTrue(result['artifact_coverage_ready'])
            self.assertEqual(result['artifact_coverage_issue_codes'], [])
            self.assertTrue(result['ready_for_controlled_presentation_review'])
            self.assertTrue(result['ready_for_controlled_presentation_package'])
            self.assertFalse(result['ready_for_sii_submission'])
            self.assertFalse(result['official_format'])
            self.assertFalse(result['sii_submission'])
            self.assertFalse(result['sii_submission_attempted'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertTrue(result['requires_official_format_gate'])
            self.assertTrue(result['requires_explicit_submission_authorization'])
            self.assertTrue(result['requires_manual_sii_step'])
            self.assertFalse(result['requires_responsible_review'])
            self.assertTrue((bundle_dir / result['presentation_bundle_manifest_file']).is_file())
            self.assertTrue((controlled_package_dir / result['controlled_package_manifest_file']).is_file())

            rendered = stdout.getvalue()
            bundle_rendered = (bundle_dir / result['presentation_bundle_manifest_file']).read_text(encoding='utf-8')
            controlled_rendered = (
                controlled_package_dir / result['controlled_package_manifest_file']
            ).read_text(encoding='utf-8')
            for sensitive_value in (
                '97030000',
                '97030000.887',
                'QA',
                '123456',
                'AAAAAAAAAAAAAAAAAAAAAAA',
                'BBBBBBBBBBBBBBBBBBBBBBB',
                'CCCCCCCCCCCCCCCCCCCCCCC',
                'TTTTTTTTTTTTTTTTTTTTTTT',
            ):
                self.assertNotIn(sensitive_value, rendered)
                self.assertNotIn(sensitive_value, bundle_rendered)
                self.assertNotIn(sensitive_value, controlled_rendered)

    def test_materialize_annual_tax_controlled_presentation_package_rejects_unapproved_checklist(self):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
        process = ProcesoRentaAnual.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        ddjj_inputs = {
            '1887': {
                'records': self._ddjj_ascii_records(ddjj_item),
                'transfer_control_record': {
                    'record': '0' + 'T' * 23,
                    'review_state': 'approved_for_candidate',
                    'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
            }
        }
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            output_dir = Path(temp_dir) / 'controlled-presentation-package'

            with self.assertRaisesMessage(CommandError, 'checklist anual aprobado'):
                call_command(
                    'materialize_annual_tax_controlled_presentation_package',
                    export_id=export.pk,
                    rut_number='97030000',
                    rut_dv='0',
                    company_code='QA',
                    client_number='123456',
                    ddjj_inputs_json=json.dumps(ddjj_inputs),
                    output_dir=str(output_dir),
                    handoff_authorization_ref='annual-tax-controlled-handoff-authorization-at2026',
                    responsible_ref='tax-reviewer-controlled-handoff-at2026',
                    presentation_window_ref='presentation-window-at2026-controlled-local',
                    package_note='controlled_handoff_without_sii_submission',
                    stdout=StringIO(),
                    **self._f22_local_certification_kwargs(),
                )

            self.assertFalse(output_dir.exists())

    def test_materialize_annual_tax_controlled_presentation_package_rejects_nonempty_output_dir(self):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
        process = ProcesoRentaAnual.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
        register_annual_tax_review_decision(
            checklist,
            review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
            decision_ref='annual-tax-manual-approval-at2026-controlled',
            decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
            responsible_ref='tax-reviewer-final-approval-controlled',
            reason='manual_review_completed_for_controlled_package',
        )
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        ddjj_inputs = {
            '1887': {
                'records': self._ddjj_ascii_records(ddjj_item),
                'transfer_control_record': {
                    'record': '0' + 'T' * 23,
                    'review_state': 'approved_for_candidate',
                    'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
            }
        }
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            output_dir = Path(temp_dir) / 'controlled-presentation-package'
            output_dir.mkdir()
            stale_file = output_dir / 'stale.txt'
            stale_file.write_text('previous presentation residue', encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'debe estar vacio'):
                call_command(
                    'materialize_annual_tax_controlled_presentation_package',
                    export_id=export.pk,
                    rut_number='97030000',
                    rut_dv='0',
                    company_code='QA',
                    client_number='123456',
                    ddjj_inputs_json=json.dumps(ddjj_inputs),
                    output_dir=str(output_dir),
                    handoff_authorization_ref='annual-tax-controlled-handoff-authorization-at2026',
                    responsible_ref='tax-reviewer-controlled-handoff-at2026',
                    presentation_window_ref='presentation-window-at2026-controlled-local',
                    package_note='controlled_handoff_without_sii_submission',
                    stdout=StringIO(),
                    **self._f22_local_certification_kwargs(),
                )

            self.assertEqual(stale_file.read_text(encoding='utf-8'), 'previous presentation residue')
            self.assertFalse((output_dir / 'presentation-review-bundle').exists())

    def test_materialize_annual_tax_controlled_presentation_package_rejects_versioned_repo_output(self):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
        process = ProcesoRentaAnual.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
        register_annual_tax_review_decision(
            checklist,
            review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
            decision_ref='annual-tax-manual-approval-at2026-controlled',
            decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
            responsible_ref='tax-reviewer-final-approval-controlled',
            reason='manual_review_completed_for_controlled_package',
        )
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        ddjj_inputs = {
            '1887': {
                'records': self._ddjj_ascii_records(ddjj_item),
                'transfer_control_record': {
                    'record': '0' + 'T' * 23,
                    'review_state': 'approved_for_candidate',
                    'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
            }
        }
        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage6-controlled-presentation-package'

        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'materialize_annual_tax_controlled_presentation_package',
                export_id=export.pk,
                rut_number='97030000',
                rut_dv='0',
                company_code='QA',
                client_number='123456',
                ddjj_inputs_json=json.dumps(ddjj_inputs),
                output_dir=str(blocked_output),
                handoff_authorization_ref='annual-tax-controlled-handoff-authorization-at2026',
                responsible_ref='tax-reviewer-controlled-handoff-at2026',
                presentation_window_ref='presentation-window-at2026-controlled-local',
                package_note='controlled_handoff_without_sii_submission',
                stdout=StringIO(),
                **self._f22_local_certification_kwargs(),
            )
        self.assertFalse(blocked_output.exists())

    def test_materialize_annual_tax_controlled_presentation_package_rejects_rut_and_local_path_refs(self):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
        process = ProcesoRentaAnual.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
        register_annual_tax_review_decision(
            checklist,
            review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
            decision_ref='annual-tax-manual-approval-at2026-controlled',
            decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
            responsible_ref='tax-reviewer-final-approval-controlled',
            reason='manual_review_completed_for_controlled_package',
        )
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        ddjj_inputs = {
            '1887': {
                'records': self._ddjj_ascii_records(ddjj_item),
                'transfer_control_record': {
                    'record': '0' + 'T' * 23,
                    'review_state': 'approved_for_candidate',
                    'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
            }
        }
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        invalid_cases = [
            ('handoff_authorization_ref', 'handoff_11.111.111-1'),
            ('presentation_window_ref', 'source_C:/Privado/presentacion.pdf'),
        ]

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            for field_name, field_value in invalid_cases:
                output_dir = Path(temp_dir) / f'controlled-presentation-package-{field_name}'
                kwargs = {
                    'handoff_authorization_ref': 'annual-tax-controlled-handoff-authorization-at2026',
                    'responsible_ref': 'tax-reviewer-controlled-handoff-at2026',
                    'presentation_window_ref': 'presentation-window-at2026-controlled-local',
                }
                kwargs[field_name] = field_value

                with self.subTest(field_name=field_name), self.assertRaisesMessage(CommandError, field_name):
                    call_command(
                        'materialize_annual_tax_controlled_presentation_package',
                        export_id=export.pk,
                        rut_number='97030000',
                        rut_dv='0',
                        company_code='QA',
                        client_number='123456',
                        ddjj_inputs_json=json.dumps(ddjj_inputs),
                        output_dir=str(output_dir),
                        package_note='controlled_handoff_without_sii_submission',
                        stdout=StringIO(),
                        **kwargs,
                        **self._f22_local_certification_kwargs(),
                    )

                self.assertFalse(output_dir.exists())

    def _materialize_controlled_presentation_package_for_certification(self, temp_dir):
        export, _mapping = self._add_reviewed_f22_fixed_width_mapping_and_resync(code='1234', value='1000')
        process = ProcesoRentaAnual.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        checklist = AnnualTaxReviewChecklist.objects.get(annual_export=export)
        register_annual_tax_review_decision(
            checklist,
            review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
            decision_ref='annual-tax-manual-approval-at2026-controlled',
            decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
            responsible_ref='tax-reviewer-final-approval-controlled',
            reason='manual_review_completed_for_controlled_package',
        )
        ddjj_item = AnnualTaxArtifactMatrixItem.objects.filter(target_kind='DDJJ', target_code='DDJJ-1887').first()
        self.assertIsNotNone(ddjj_item)
        ddjj_inputs = {
            '1887': {
                'records': self._ddjj_ascii_records(ddjj_item),
                'transfer_control_record': {
                    'record': '0' + 'T' * 23,
                    'review_state': 'approved_for_candidate',
                    'transfer_source_ref': 'sii-ddjj-at2026-transfer-control-reviewed',
                    'responsible_review_ref': 'tax-reviewer-at2026-controlled',
                },
            }
        }
        output_dir = Path(temp_dir) / 'controlled-presentation-package'
        call_command(
            'materialize_annual_tax_controlled_presentation_package',
            export_id=export.pk,
            rut_number='97030000',
            rut_dv='0',
            company_code='QA',
            client_number='123456',
            ddjj_inputs_json=json.dumps(ddjj_inputs),
            output_dir=str(output_dir),
            handoff_authorization_ref='annual-tax-controlled-handoff-authorization-at2026',
            responsible_ref='tax-reviewer-controlled-handoff-at2026',
            presentation_window_ref='presentation-window-at2026-controlled-local',
            package_note='controlled_handoff_without_sii_submission',
            stdout=StringIO(),
            **self._f22_local_certification_kwargs(),
        )
        return {
            'export': export,
            'output_dir': output_dir,
            'controlled_package_dir': output_dir / 'controlled-presentation-handoff',
        }

    def test_materialize_annual_tax_sii_certification_readiness_packet_blocks_submission_without_external_refs(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            fixture = self._materialize_controlled_presentation_package_for_certification(temp_dir)
            output_dir = Path(temp_dir) / 'sii-certification-readiness'
            stdout = StringIO()

            call_command(
                'materialize_annual_tax_sii_certification_readiness_packet',
                controlled_package_dir=str(fixture['controlled_package_dir']),
                output_dir=str(output_dir),
                certification_review_ref='stage6-sii-certification-readiness-review-at2026',
                responsible_ref='tax-reviewer-sii-certification-readiness-at2026',
                packet_note='readiness_review_without_sii_submission',
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            verification = verify_annual_tax_sii_certification_readiness_packet(
                fixture['controlled_package_dir'],
                output_dir,
                certification_review_ref='stage6-sii-certification-readiness-review-at2026',
                responsible_ref='tax-reviewer-sii-certification-readiness-at2026',
                packet_note='readiness_review_without_sii_submission',
            )

            self.assertTrue(result['materialized'])
            self.assertEqual(result['packet_hash'], verification['packet_hash'])
            self.assertEqual(result['classification'], 'preparado_para_certificacion_externa_con_bloqueos')
            self.assertEqual(result['external_requirements_total'], 8)
            self.assertEqual(result['external_requirements_provided_total'], 0)
            self.assertEqual(
                set(result['missing_external_gate_keys']),
                {
                    'official_format_gate',
                    'f22_certification_authorization',
                    'ddjj_certification_or_upload_path',
                    'sii_authenticated_environment',
                    'explicit_submission_authorization',
                    'responsible_tax_signoff',
                    'rollback_plan',
                    'evidence_archive',
                },
            )
            self.assertFalse(result['ready_for_external_certification_review'])
            self.assertFalse(result['ready_for_sii_submission'])
            self.assertFalse(result['official_format'])
            self.assertFalse(result['official_submission_allowed'])
            self.assertFalse(result['sii_submission'])
            self.assertFalse(result['sii_submission_attempted'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertTrue(result['requires_external_sii_certification'])
            self.assertTrue(result['requires_explicit_submission_authorization'])
            self.assertTrue(result['requires_manual_sii_step'])
            self.assertTrue((output_dir / result['manifest_file']).is_file())

            rendered = stdout.getvalue()
            manifest = (output_dir / result['manifest_file']).read_text(encoding='utf-8')
            for sensitive_value in (
                '97030000',
                '97030000.887',
                'QA',
                '123456',
                'AAAAAAAAAAAAAAAAAAAAAAA',
                'BBBBBBBBBBBBBBBBBBBBBBB',
                'CCCCCCCCCCCCCCCCCCCCCCC',
                'TTTTTTTTTTTTTTTTTTTTTTT',
            ):
                self.assertNotIn(sensitive_value, rendered)
                self.assertNotIn(sensitive_value, manifest)

    def test_materialize_annual_tax_sii_certification_readiness_packet_with_external_refs_still_blocks_submission(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            fixture = self._materialize_controlled_presentation_package_for_certification(temp_dir)
            output_dir = Path(temp_dir) / 'sii-certification-readiness'
            stdout = StringIO()
            external_refs = {
                'official_format_authorization_ref': 'sii-at2026-official-format-reviewed',
                'f22_certification_authorization_ref': 'sii-f22-at2026-certification-reviewed',
                'ddjj_certification_authorization_ref': 'sii-ddjj-at2026-upload-reviewed',
                'sii_environment_ref': 'sii-supervised-environment-at2026-reviewed',
                'submission_authorization_ref': 'explicit-submission-authorization-at2026-reviewed',
                'responsible_tax_signoff_ref': 'tax-responsible-signoff-at2026-reviewed',
                'rollback_plan_ref': 'sii-presentation-rollback-plan-at2026-reviewed',
                'evidence_archive_ref': 'sii-presentation-evidence-archive-at2026-reviewed',
            }

            call_command(
                'materialize_annual_tax_sii_certification_readiness_packet',
                controlled_package_dir=str(fixture['controlled_package_dir']),
                output_dir=str(output_dir),
                certification_review_ref='stage6-sii-certification-readiness-review-at2026',
                responsible_ref='tax-reviewer-sii-certification-readiness-at2026',
                packet_note='readiness_review_without_sii_submission',
                stdout=stdout,
                **external_refs,
            )

            result = json.loads(stdout.getvalue())
            verification = verify_annual_tax_sii_certification_readiness_packet(
                fixture['controlled_package_dir'],
                output_dir,
                certification_review_ref='stage6-sii-certification-readiness-review-at2026',
                responsible_ref='tax-reviewer-sii-certification-readiness-at2026',
                packet_note='readiness_review_without_sii_submission',
                **external_refs,
            )

            self.assertEqual(result['packet_hash'], verification['packet_hash'])
            self.assertEqual(result['classification'], 'preparado_para_revision_externa_no_envio')
            self.assertEqual(result['external_requirements_total'], 8)
            self.assertEqual(result['external_requirements_provided_total'], 8)
            self.assertEqual(result['missing_external_gate_keys'], [])
            self.assertTrue(result['ready_for_external_certification_review'])
            self.assertFalse(result['ready_for_sii_submission'])
            self.assertFalse(result['official_format'])
            self.assertFalse(result['official_submission_allowed'])
            self.assertFalse(result['sii_submission'])
            self.assertFalse(result['sii_submission_attempted'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertTrue(result['requires_external_sii_certification'])
            self.assertTrue(result['requires_explicit_submission_authorization'])
            self.assertTrue(result['requires_manual_sii_step'])

    def test_materialize_annual_tax_sii_certification_readiness_packet_rejects_sensitive_external_refs(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            fixture = self._materialize_controlled_presentation_package_for_certification(temp_dir)
            output_dir = Path(temp_dir) / 'sii-certification-readiness'

            with self.assertRaisesMessage(CommandError, 'sii_environment_ref'):
                call_command(
                    'materialize_annual_tax_sii_certification_readiness_packet',
                    controlled_package_dir=str(fixture['controlled_package_dir']),
                    output_dir=str(output_dir),
                    certification_review_ref='stage6-sii-certification-readiness-review-at2026',
                    responsible_ref='tax-reviewer-sii-certification-readiness-at2026',
                    sii_environment_ref='https://www.sii.cl/session?token=secret',
                    stdout=StringIO(),
                )

            self.assertFalse(output_dir.exists())

    def test_materialize_annual_tax_sii_certification_readiness_packet_rejects_rut_and_local_path_refs(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            fixture = self._materialize_controlled_presentation_package_for_certification(temp_dir)
            invalid_cases = [
                ('certification_review_ref', 'review_11.111.111-1'),
                ('official_format_authorization_ref', 'source_C:/Privado/formato-oficial.pdf'),
            ]

            for field_name, field_value in invalid_cases:
                output_dir = Path(temp_dir) / f'sii-certification-readiness-{field_name}'
                kwargs = {
                    'certification_review_ref': 'stage6-sii-certification-readiness-review-at2026',
                    'responsible_ref': 'tax-reviewer-sii-certification-readiness-at2026',
                }
                kwargs[field_name] = field_value

                with self.subTest(field_name=field_name), self.assertRaisesMessage(CommandError, field_name):
                    call_command(
                        'materialize_annual_tax_sii_certification_readiness_packet',
                        controlled_package_dir=str(fixture['controlled_package_dir']),
                        output_dir=str(output_dir),
                        stdout=StringIO(),
                        **kwargs,
                    )

                self.assertFalse(output_dir.exists())

    def test_materialize_annual_tax_sii_certification_readiness_packet_rejects_nonempty_output_dir(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            fixture = self._materialize_controlled_presentation_package_for_certification(temp_dir)
            output_dir = Path(temp_dir) / 'sii-certification-readiness'
            output_dir.mkdir()
            stale_file = output_dir / 'stale.txt'
            stale_file.write_text('previous certification readiness residue', encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'debe estar vacio'):
                call_command(
                    'materialize_annual_tax_sii_certification_readiness_packet',
                    controlled_package_dir=str(fixture['controlled_package_dir']),
                    output_dir=str(output_dir),
                    certification_review_ref='stage6-sii-certification-readiness-review-at2026',
                    responsible_ref='tax-reviewer-sii-certification-readiness-at2026',
                    stdout=StringIO(),
                )

            self.assertTrue(stale_file.exists())

    def test_materialize_annual_tax_sii_certification_readiness_packet_rejects_versioned_repo_output(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            fixture = self._materialize_controlled_presentation_package_for_certification(temp_dir)
            blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage6-certification-readiness'

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'materialize_annual_tax_sii_certification_readiness_packet',
                    controlled_package_dir=str(fixture['controlled_package_dir']),
                    output_dir=str(blocked_output),
                    certification_review_ref='stage6-sii-certification-readiness-review-at2026',
                    responsible_ref='tax-reviewer-sii-certification-readiness-at2026',
                    stdout=StringIO(),
                )

            self.assertFalse(blocked_output.exists())

    def test_materialize_annual_tax_presentation_review_bundle_rejects_nonempty_output_dir(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            inputs = self._materialize_presentation_review_inputs(temp_dir)
            output_dir = Path(temp_dir) / 'presentation-review-bundle'
            output_dir.mkdir()
            stale_file = output_dir / 'stale.txt'
            stale_file.write_text('previous presentation review residue', encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'debe estar vacio'):
                call_command(
                    'materialize_annual_tax_presentation_review_bundle',
                    export_id=inputs['export'].pk,
                    export_package_dir=str(inputs['export_package_dir']),
                    f22_candidate_dir=str(inputs['f22_dir']),
                    ddjj_ascii_candidate_dir=[str(inputs['ddjj_ascii_dir'])],
                    ddjj_zip_candidate_dir=[str(inputs['ddjj_zip_dir'])],
                    output_dir=str(output_dir),
                    stdout=StringIO(),
                )

            self.assertEqual(stale_file.read_text(encoding='utf-8'), 'previous presentation review residue')
            self.assertFalse((output_dir / 'annual-tax-presentation-review-bundle.json').exists())

    def test_materialize_annual_tax_presentation_review_bundle_rejects_versioned_repo_output(self):
        self._create_valid_local_matrix()
        export = AnnualTaxExport.objects.get()
        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage6-presentation-review-bundle'

        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'materialize_annual_tax_presentation_review_bundle',
                export_id=export.pk,
                output_dir=str(blocked_output),
                stdout=StringIO(),
            )
        self.assertFalse(blocked_output.exists())

    def test_tax_export_missing_artifact_contracts_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        export = AnnualTaxExport.objects.get()
        payload = dict(export.export_payload)
        payload.pop('export_artifact_contracts')
        payload.pop('export_contracts_total')
        hash_export = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')
        ).hexdigest()
        AnnualTaxExport.objects.filter(pk=export.pk).update(
            export_payload=payload,
            hash_export=hash_export,
        )
        summary = dict(process.resumen_anual)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_export_invalid', issue_codes)
        self.assertIn('stage6.tax_export_artifact_contracts_missing', issue_codes)

    def test_tax_export_missing_file_manifest_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        export = AnnualTaxExport.objects.get()
        payload = dict(export.export_payload)
        payload.pop('export_file_manifest')
        payload.pop('export_files_total')
        payload.pop('ddjj_export_files_total')
        payload.pop('f22_export_files_total')
        payload.pop('export_file_manifest_hash')
        hash_export = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')
        ).hexdigest()
        AnnualTaxExport.objects.filter(pk=export.pk).update(
            export_payload=payload,
            hash_export=hash_export,
        )
        summary = dict(process.resumen_anual)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_export_invalid', issue_codes)
        self.assertIn('stage6.tax_export_file_manifest_missing', issue_codes)

    def test_tax_export_missing_file_package_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        export = AnnualTaxExport.objects.get()
        payload = dict(export.export_payload)
        payload.pop('export_file_package_manifest')
        payload.pop('export_file_package_version')
        payload.pop('export_file_package_files_total')
        payload.pop('ddjj_export_package_files_total')
        payload.pop('f22_export_package_files_total')
        payload.pop('export_file_package_hash')
        hash_export = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')
        ).hexdigest()
        AnnualTaxExport.objects.filter(pk=export.pk).update(
            export_payload=payload,
            hash_export=hash_export,
        )
        summary = dict(process.resumen_anual)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_export_invalid', issue_codes)
        self.assertIn('stage6.tax_export_file_package_missing', issue_codes)

    def test_tax_export_artifact_contract_boundary_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        export = AnnualTaxExport.objects.get()
        payload = dict(export.export_payload)
        contracts = [dict(contract) for contract in payload['export_artifact_contracts']]
        contracts[0]['official_format'] = True
        contracts[0]['sii_submission'] = True
        contracts[0]['final_tax_calculation'] = True
        payload['export_artifact_contracts'] = contracts
        hash_export = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')
        ).hexdigest()
        AnnualTaxExport.objects.filter(pk=export.pk).update(
            export_payload=payload,
            hash_export=hash_export,
        )
        summary = dict(process.resumen_anual)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_export_invalid', issue_codes)
        self.assertIn('stage6.tax_export_artifact_contract_boundary', issue_codes)

    def test_tax_export_file_manifest_boundary_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        export = AnnualTaxExport.objects.get()
        payload = dict(export.export_payload)
        file_manifest = [dict(entry) for entry in payload['export_file_manifest']]
        file_manifest[0]['official_format'] = True
        file_manifest[0]['sii_submission'] = True
        file_manifest[0]['final_tax_calculation'] = True
        payload['export_file_manifest'] = file_manifest
        hash_export = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')
        ).hexdigest()
        AnnualTaxExport.objects.filter(pk=export.pk).update(
            export_payload=payload,
            hash_export=hash_export,
        )
        summary = dict(process.resumen_anual)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_export_invalid', issue_codes)
        self.assertIn('stage6.tax_export_file_manifest_boundary', issue_codes)

    def test_tax_export_file_package_boundary_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        export = AnnualTaxExport.objects.get()
        payload = dict(export.export_payload)
        package_manifest = [dict(entry) for entry in payload['export_file_package_manifest']]
        package_manifest[0]['official_format'] = True
        package_manifest[0]['sii_submission'] = True
        package_manifest[0]['final_tax_calculation'] = True
        payload['export_file_package_manifest'] = package_manifest
        hash_export = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')
        ).hexdigest()
        AnnualTaxExport.objects.filter(pk=export.pk).update(
            export_payload=payload,
            hash_export=hash_export,
        )
        summary = dict(process.resumen_anual)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_export_invalid', issue_codes)
        self.assertIn('stage6.tax_export_file_package_boundary', issue_codes)

    def test_invalid_tax_export_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxExport.objects.update(
            source_ref='https://sii.example.test/export?token=secret',
            responsible_ref='Bearer tax-export-secret',
            export_ref='https://sii.example.test/export-file?token=secret',
            export_payload={'api_key': 'secret-tax-export'},
            hash_export='not-a-sha',
            official_format=True,
            sii_submission=True,
            final_tax_calculation=True,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_export_invalid', issue_codes)
        self.assertIn('stage6.tax_export_official_format_boundary', issue_codes)
        self.assertIn('stage6.tax_export_sii_submission_boundary', issue_codes)
        self.assertIn('stage6.tax_export_final_calculation_boundary', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('tax-export-secret', serialized_result)

    def test_annual_process_without_tax_review_checklist_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxReviewChecklist.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_review_checklist_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_review_checklists']['checklists_total'], 0)

    def test_tax_review_checklist_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        checklist_summary = dict(summary['annual_tax_review_checklists'])
        by_id = dict(checklist_summary['by_id'])
        checklist_id = next(iter(by_id.keys()))
        item_summary = dict(by_id[checklist_id])
        item_summary['hash_checklist'] = 'e' * 64
        by_id[checklist_id] = item_summary
        checklist_summary['by_id'] = by_id
        summary['annual_tax_review_checklists'] = checklist_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_review_checklist_summary_mismatch', issue_codes)

    def test_invalid_tax_review_checklist_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxReviewChecklist.objects.update(
            checklist_ref='https://sii.example.test/checklist?token=secret',
            responsible_ref='Bearer tax-checklist-secret',
            evidence_ref='https://sii.example.test/evidence?token=secret',
            review_payload={'api_key': 'secret-tax-checklist'},
            hash_checklist='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_review_checklist_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('tax-checklist-secret', serialized_result)

    def test_tax_review_checklist_boundary_flags_are_blocking(self):
        self._create_valid_local_matrix()
        checklist = AnnualTaxReviewChecklist.objects.get()
        process = checklist.proceso_renta_anual
        review_payload = dict(checklist.review_payload)
        review_payload.update(
            {
                'official_format': True,
                'sii_submission': True,
                'sii_submission_attempted': True,
                'final_tax_calculation': True,
            }
        )
        hash_checklist = hashlib.sha256(
            json.dumps(
                review_payload,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        AnnualTaxReviewChecklist.objects.filter(pk=checklist.pk).update(
            review_payload=review_payload,
            hash_checklist=hash_checklist,
        )
        process_summary = dict(process.resumen_anual)
        checklist_process_summary = dict(process_summary['annual_tax_review_checklists'])
        by_id = dict(checklist_process_summary['by_id'])
        item_summary = dict(by_id[str(checklist.id)])
        item_summary['hash_checklist'] = hash_checklist
        by_id[str(checklist.id)] = item_summary
        checklist_process_summary['by_id'] = by_id
        process_summary['annual_tax_review_checklists'] = checklist_process_summary
        process.resumen_anual = process_summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_review_checklist_invalid', issue_codes)
        self.assertIn('stage6.tax_review_checklist_official_format_boundary', issue_codes)
        self.assertIn('stage6.tax_review_checklist_sii_submission_boundary', issue_codes)
        self.assertIn('stage6.tax_review_checklist_final_calculation_boundary', issue_codes)

    def test_tax_review_checklist_records_non_automatic_review_decision_boundary(self):
        self._create_valid_local_matrix()
        checklist = AnnualTaxReviewChecklist.objects.get()
        payload = checklist.review_payload
        review_decision = payload['review_decision']

        self.assertEqual(
            checklist.review_decision_state,
            EstadoAnnualTaxReviewDecision.PREPARED,
        )
        self.assertEqual(
            payload['review_decision_state'],
            EstadoAnnualTaxReviewDecision.PREPARED,
        )
        self.assertEqual(review_decision['state'], EstadoAnnualTaxReviewDecision.PREPARED)
        self.assertEqual(checklist.review_decision_ref, review_decision['decision_ref'])
        self.assertEqual(checklist.review_decision_evidence_ref, review_decision['evidence_ref'])
        self.assertEqual(payload['review_decision_ref'], checklist.review_decision_ref)
        self.assertEqual(payload['review_decision_evidence_ref'], checklist.review_decision_evidence_ref)
        self.assertFalse(review_decision['ready_for_presentation'])
        self.assertFalse(review_decision['automatic_approval'])
        self.assertTrue(review_decision['approval_required_for_presentation'])

    def test_tax_review_checklist_observed_decision_is_blocking(self):
        self._create_valid_local_matrix()
        checklist = AnnualTaxReviewChecklist.objects.get()
        process = checklist.proceso_renta_anual
        review_payload = dict(checklist.review_payload)
        review_decision = dict(review_payload['review_decision'])
        review_payload['review_decision_state'] = EstadoAnnualTaxReviewDecision.OBSERVED
        review_decision.update(
            {
                'state': EstadoAnnualTaxReviewDecision.OBSERVED,
                'reason': 'manual_observation_requires_resolution',
                'ready_for_presentation': False,
                'automatic_approval': False,
            }
        )
        review_payload['review_decision'] = review_decision
        hash_checklist = hashlib.sha256(
            json.dumps(
                review_payload,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        AnnualTaxReviewChecklist.objects.filter(pk=checklist.pk).update(
            review_decision_state=EstadoAnnualTaxReviewDecision.OBSERVED,
            review_payload=review_payload,
            hash_checklist=hash_checklist,
        )
        process_summary = dict(process.resumen_anual)
        checklist_process_summary = dict(process_summary['annual_tax_review_checklists'])
        by_id = dict(checklist_process_summary['by_id'])
        item_summary = dict(by_id[str(checklist.id)])
        item_summary['hash_checklist'] = hash_checklist
        item_summary['review_decision_state'] = EstadoAnnualTaxReviewDecision.OBSERVED
        item_summary['review_decision_evidence_ref'] = checklist.review_decision_evidence_ref
        by_id[str(checklist.id)] = item_summary
        checklist_process_summary['by_id'] = by_id
        process_summary['annual_tax_review_checklists'] = checklist_process_summary
        process.resumen_anual = process_summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_review_checklist_observed', issue_codes)

    def test_tax_review_checklist_automatic_approval_is_blocking(self):
        self._create_valid_local_matrix()
        checklist = AnnualTaxReviewChecklist.objects.get()
        process = checklist.proceso_renta_anual
        review_payload = dict(checklist.review_payload)
        review_decision = dict(review_payload['review_decision'])
        approval_ref = 'annual-tax-manual-approval-at2026-controlled'
        approval_evidence_ref = 'annual-tax-manual-approval-evidence-at2026-controlled'
        review_payload['review_decision_state'] = EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION
        review_payload['review_decision_ref'] = approval_ref
        review_payload['review_decision_evidence_ref'] = approval_evidence_ref
        review_decision.update(
            {
                'state': EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
                'decision_ref': approval_ref,
                'evidence_ref': approval_evidence_ref,
                'responsible_ref': 'tax-reviewer-final-approval-controlled',
                'reason': 'manual_approval_recorded_for_test',
                'ready_for_presentation': True,
                'automatic_approval': True,
            }
        )
        review_payload['review_decision'] = review_decision
        hash_checklist = hashlib.sha256(
            json.dumps(
                review_payload,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        AnnualTaxReviewChecklist.objects.filter(pk=checklist.pk).update(
            review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
            review_decision_ref=approval_ref,
            review_decision_evidence_ref=approval_evidence_ref,
            review_payload=review_payload,
            hash_checklist=hash_checklist,
        )
        process_summary = dict(process.resumen_anual)
        checklist_process_summary = dict(process_summary['annual_tax_review_checklists'])
        by_id = dict(checklist_process_summary['by_id'])
        item_summary = dict(by_id[str(checklist.id)])
        item_summary['hash_checklist'] = hash_checklist
        item_summary['review_decision_state'] = EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION
        item_summary['review_decision_ref'] = approval_ref
        item_summary['review_decision_evidence_ref'] = approval_evidence_ref
        by_id[str(checklist.id)] = item_summary
        checklist_process_summary['by_id'] = by_id
        process_summary['annual_tax_review_checklists'] = checklist_process_summary
        process.resumen_anual = process_summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_review_checklist_invalid', issue_codes)
        self.assertIn('stage6.tax_review_checklist_approval_incoherent', issue_codes)

    def test_tax_review_checklist_approval_without_evidence_is_blocking(self):
        self._create_valid_local_matrix()
        checklist = AnnualTaxReviewChecklist.objects.get()
        process = checklist.proceso_renta_anual
        review_payload = dict(checklist.review_payload)
        review_decision = dict(review_payload['review_decision'])
        approval_ref = 'annual-tax-manual-approval-at2026-controlled'
        review_payload['review_decision_state'] = EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION
        review_payload['review_decision_ref'] = approval_ref
        review_payload.pop('review_decision_evidence_ref', None)
        review_decision.update(
            {
                'state': EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
                'decision_ref': approval_ref,
                'responsible_ref': 'tax-reviewer-final-approval-controlled',
                'reason': 'manual_approval_recorded_without_evidence_for_test',
                'ready_for_presentation': True,
                'automatic_approval': False,
            }
        )
        review_decision.pop('evidence_ref', None)
        review_payload['review_decision'] = review_decision
        hash_checklist = hashlib.sha256(
            json.dumps(
                review_payload,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        AnnualTaxReviewChecklist.objects.filter(pk=checklist.pk).update(
            review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
            review_decision_ref=approval_ref,
            review_decision_evidence_ref='',
            review_payload=review_payload,
            hash_checklist=hash_checklist,
        )
        process_summary = dict(process.resumen_anual)
        checklist_process_summary = dict(process_summary['annual_tax_review_checklists'])
        by_id = dict(checklist_process_summary['by_id'])
        item_summary = dict(by_id[str(checklist.id)])
        item_summary['hash_checklist'] = hash_checklist
        item_summary['review_decision_state'] = EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION
        item_summary['review_decision_ref'] = approval_ref
        item_summary['review_decision_evidence_ref'] = ''
        by_id[str(checklist.id)] = item_summary
        checklist_process_summary['by_id'] = by_id
        process_summary['annual_tax_review_checklists'] = checklist_process_summary
        process.resumen_anual = process_summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_review_checklist_invalid', issue_codes)
        self.assertIn('stage6.tax_review_checklist_approval_missing', issue_codes)

    def test_tax_review_checklist_approval_with_official_compatibility_gap_is_blocking(self):
        self._create_valid_local_matrix()
        checklist = AnnualTaxReviewChecklist.objects.get()
        register_annual_tax_review_decision(
            checklist,
            review_decision_state=EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION,
            decision_ref='annual-tax-manual-approval-at2026-controlled',
            decision_evidence_ref='annual-tax-manual-approval-evidence-at2026-controlled',
            responsible_ref='tax-reviewer-final-approval-controlled',
            reason='manual_review_completed_with_official_gap_for_readiness',
        )
        compatibility_gap = {
            'ready_for_controlled_presentation_approval': False,
            'issue_codes': [],
            'blocking_gap_keys': ['f22_record_format_2025'],
        }

        with patch(
            'core.stage6_renta_anual_readiness.summarize_stage6_official_compatibility_for_presentation',
            return_value=compatibility_gap,
        ):
            result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_review_checklist_official_compatibility_gap', issue_codes)

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

    def test_annual_process_without_source_bundle_is_blocking(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(source_bundle=None)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_source_bundle_missing', issue_codes)
        self.assertEqual(result['sections']['annual_process']['process_source_bundle_missing'], 1)

    def test_invalid_annual_source_bundle_is_blocking_without_sensitive_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxSourceBundle.objects.update(
            source_label='https://sii.example.test/source?token=secret',
            hash_fuentes='bad-hash',
            resumen_fuentes={'api_key': 'secret'},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.source_bundle_invalid', issue_codes)
        self.assertNotIn('sii.example.test', serialized_result)
        self.assertNotIn('token=secret', serialized_result)

    def test_annual_process_source_bundle_summary_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_source_bundle': {
                **process.resumen_anual['annual_tax_source_bundle'],
                'hash_fuentes': 'f' * 64,
            },
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_source_bundle_summary_mismatch', issue_codes)

    def test_annual_process_without_monthly_tax_facts_is_blocking(self):
        self._create_valid_local_matrix()
        MonthlyTaxFact.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.monthly_tax_fact_missing', issue_codes)
        self.assertIn('stage6.process_monthly_tax_facts_missing', issue_codes)
        self.assertEqual(result['sections']['monthly_tax_facts']['process_monthly_tax_facts_missing'], 1)

    def test_invalid_monthly_tax_fact_is_blocking_without_sensitive_leak(self):
        self._create_valid_local_matrix()
        MonthlyTaxFact.objects.filter(mes=1).update(
            source_ref='https://sii.example.test/monthly?token=secret',
            hash_hecho='bad-hash',
            resumen_hecho={'api_key': 'secret-monthly-value'},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.monthly_tax_fact_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('secret-monthly-value', serialized_result)

    def test_monthly_tax_fact_summary_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_monthly_facts': {
                **process.resumen_anual['annual_tax_monthly_facts'],
                'months': list(range(1, 12)),
            },
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_monthly_tax_fact_summary_mismatch', issue_codes)

    def test_annual_process_without_rli_cpt_workbooks_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualEnterpriseRegisterSet.objects.all().delete()
        AnnualTaxWorkbookLine.objects.all().delete()
        AnnualTaxWorkbook.objects.all().delete()
        process = ProcesoRentaAnual.objects.get()
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_workbooks': {'total': 2, 'types': ['CPT', 'RLI'], 'by_type': {}},
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_workbooks_missing', issue_codes)
        self.assertIn('stage6.process_tax_workbook_summary_mismatch', issue_codes)
        self.assertEqual(result['sections']['annual_tax_workbooks']['process_tax_workbooks_missing'], 1)

    def test_invalid_annual_tax_workbook_line_is_blocking_without_sensitive_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxWorkbookLine.objects.filter(codigo_destino='RLI-ING-001').update(
            origen='',
            formula_ref='https://sii.example.test/formula?token=secret',
            evidencia_ref='Bearer annual-line-secret',
            source_payload={'api_key': 'secret-line-value'},
            hash_linea='bad-hash',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_workbook_line_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('secret-line-value', serialized_result)

    def test_annual_tax_workbook_summary_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_workbooks': {
                **summarize_annual_tax_workbooks(process),
                'by_type': {
                    **summarize_annual_tax_workbooks(process)['by_type'],
                    'RLI': {
                        **summarize_annual_tax_workbooks(process)['by_type']['RLI'],
                        'hash_workbook': 'f' * 64,
                    },
                },
            },
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_workbook_summary_mismatch', issue_codes)

    def test_annual_process_without_approved_tax_year_ruleset_is_blocking(self):
        self._create_valid_local_matrix()
        TaxYearRuleSet.objects.update(estado=EstadoReglaTributariaAnual.DRAFT)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_year_ruleset_missing', issue_codes)
        self.assertEqual(result['sections']['tax_year_rules']['tax_year_ruleset_missing'], 1)

    def test_approved_tax_year_ruleset_without_mapping_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualEnterpriseRegisterSet.objects.all().delete()
        AnnualTaxWorkbookLine.objects.all().delete()
        AnnualTaxWorkbook.objects.all().delete()
        TaxCodeMapping.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_code_mapping_missing', issue_codes)
        self.assertEqual(result['sections']['tax_year_rules']['tax_code_mapping_missing'], 1)

    def test_approved_tax_rules_without_official_source_are_blocking(self):
        self._create_valid_local_matrix()
        TaxYearRuleSet.objects.update(official_source=None)
        TaxCodeMapping.objects.update(official_source=None)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_year_ruleset_official_source_missing', issue_codes)
        self.assertIn('stage6.tax_code_mapping_official_source_missing', issue_codes)
        self.assertEqual(result['sections']['tax_year_rules']['tax_year_ruleset_official_source_missing'], 1)
        self.assertEqual(result['sections']['tax_year_rules']['tax_code_mapping_official_source_missing'], 4)

    def test_invalid_tax_year_rules_are_blocking_without_sensitive_leak(self):
        self._create_valid_local_matrix()
        TaxYearRuleSet.objects.update(
            fuente_ref='https://sii.example.test/rule?token=secret',
            hash_normativo='bad-hash',
        )
        TaxCodeMapping.objects.update(
            formula_ref='https://sii.example.test/formula?token=secret',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_year_ruleset_invalid', issue_codes)
        self.assertIn('stage6.tax_code_mapping_invalid', issue_codes)
        self.assertNotIn('sii.example.test', serialized_result)
        self.assertNotIn('token=secret', serialized_result)

    def test_trial_balance_mapping_without_classifier_is_blocking(self):
        self._create_valid_local_matrix()
        rli_mapping = TaxCodeMapping.objects.get(destino=DestinoMapeoTributarioAnual.RLI)
        rai_mapping = TaxCodeMapping.objects.get(destino=DestinoMapeoTributarioAnual.RAI)
        TaxCodeMapping.objects.filter(pk=rli_mapping.pk).update(
            metadata={
                'source': 'stage6-controlled',
                'source_metric': 'annual_trial_balance.resultado_ganancia_clp',
            },
        )
        TaxCodeMapping.objects.filter(pk=rai_mapping.pk).update(
            metadata={
                'source': 'stage6-controlled',
                'source_metric': 'annual_trial_balance.resultado_ganancia_clp',
                'trial_balance_classifier': 'RLI-LEASE-REVENUE',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_code_mapping_invalid', issue_codes)
        self.assertIn('stage6.tax_code_mapping_trial_balance_classifier_missing', issue_codes)
        self.assertIn('stage6.tax_code_mapping_trial_balance_destination_invalid', issue_codes)
        self.assertEqual(
            result['sections']['tax_year_rules']['tax_code_mapping_trial_balance_classifier_missing'],
            1,
        )
        self.assertEqual(
            result['sections']['tax_year_rules']['tax_code_mapping_trial_balance_destination_invalid'],
            1,
        )

    def test_invalid_annual_tax_official_source_is_blocking_without_sensitive_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxOfficialSource.objects.create(
            anio_tributario=2026,
            source_key='sii-f22-invalid-at2026',
            source_type=TipoAnnualTaxOfficialSource.SII_F22_CERTIFICATION,
            title='Certificacion F22 AT2026',
            source_url='https://www.sii.cl/noticias/2026/060226noti02pcr.htm?token=secret',
            source_ref='Bearer source-secret',
            source_hash='bad-hash',
            retrieved_on=date(2026, 6, 14),
            responsible_ref='https://sii.example.test/reviewer?token=secret',
            metadata={'credential': 'secret'},
            estado=EstadoAnnualTaxOfficialSource.APPROVED,
            applies_to=DestinoMapeoTributarioAnual.F22,
            form_code='F22',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.official_source_invalid', issue_codes)
        self.assertEqual(result['sections']['annual_tax_official_sources']['official_source_invalid'], 1)
        self.assertEqual(result['sections']['annual_tax_official_sources']['sources_total'], 10)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('source-secret', serialized_result)

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

    def test_approved_annual_artifacts_without_review_responsible_are_blocking(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(responsable_revision_ref='')
        DDJJPreparacionAnual.objects.update(responsable_revision_ref='')
        F22PreparacionAnual.objects.update(responsable_revision_ref='')

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_responsible_ref_missing', issue_codes)
        self.assertIn('stage6.ddjj_responsible_ref_missing', issue_codes)
        self.assertIn('stage6.f22_responsible_ref_missing', issue_codes)
        self.assertEqual(result['sections']['annual_process']['process_responsible_ref_missing'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_responsible_ref_missing'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_responsible_ref_missing'], 1)

    def test_sensitive_annual_final_refs_are_classified_explicitly(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(
            paquete_ddjj_ref='https://sii.example.test/ddjj?token=secret',
            borrador_f22_ref='https://sii.example.test/f22?token=secret',
            responsable_revision_ref='https://sii.example.test/user?token=secret',
        )
        DDJJPreparacionAnual.objects.update(
            paquete_ref='https://sii.example.test/ddjj?token=secret',
            responsable_revision_ref='https://sii.example.test/user?token=secret',
        )
        F22PreparacionAnual.objects.update(
            borrador_ref='https://sii.example.test/f22?token=secret',
            responsable_revision_ref='https://sii.example.test/user?token=secret',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_ddjj_ref_sensitive', issue_codes)
        self.assertIn('stage6.process_f22_ref_sensitive', issue_codes)
        self.assertIn('stage6.process_responsible_ref_sensitive', issue_codes)
        self.assertIn('stage6.ddjj_ref_sensitive', issue_codes)
        self.assertIn('stage6.f22_ref_sensitive', issue_codes)
        self.assertIn('stage6.ddjj_responsible_ref_sensitive', issue_codes)
        self.assertIn('stage6.f22_responsible_ref_sensitive', issue_codes)
        self.assertEqual(result['sections']['annual_process']['process_ddjj_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_process']['process_f22_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_process']['process_responsible_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_responsible_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_responsible_ref_sensitive'], 1)
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
