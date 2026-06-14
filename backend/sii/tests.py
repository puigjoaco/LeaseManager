import hashlib
import json
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from cobranza.models import PagoMensual
from cobranza.services import sync_payment_distribution
from contabilidad.models import CierreMensualContable, ConfiguracionFiscalEmpresa, ObligacionTributariaMensual, RegimenTributarioEmpresa
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual

from .admin import (
    AnnualEnterpriseRegisterMovementAdmin,
    AnnualEnterpriseRegisterSetAdmin,
    AnnualRealEstateItemAdmin,
    AnnualRealEstateSectionAdmin,
    AnnualTaxArtifactMatrixAdmin,
    AnnualTaxArtifactMatrixItemAdmin,
    AnnualTaxSourceBundleAdmin,
    AnnualTaxWorkbookAdmin,
    AnnualTaxWorkbookLineAdmin,
    CapacidadTributariaSIIAdmin,
    DDJJPreparacionAnualAdmin,
    DTEEmitidoAdmin,
    F22PreparacionAnualAdmin,
    F29PreparacionMensualAdmin,
    MonthlyTaxFactAdmin,
    ProcesoRentaAnualAdmin,
    TaxCodeMappingAdmin,
    TaxYearRuleSetAdmin,
)
from .models import (
    AnnualEnterpriseRegisterMovement,
    AnnualEnterpriseRegisterSet,
    AnnualRealEstateItem,
    AnnualRealEstateSection,
    AnnualTaxArtifactMatrix,
    AnnualTaxArtifactMatrixItem,
    AnnualTaxSourceBundle,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    DestinoMapeoTributarioAnual,
    DTEEmitido,
    EstadoGateSII,
    EstadoAnnualTaxSourceBundle,
    EstadoMonthlyTaxFact,
    EstadoReglaTributariaAnual,
    F22PreparacionAnual,
    F29PreparacionMensual,
    MonthlyTaxFact,
    ProcesoRentaAnual,
    SourceKindRentaAnual,
    TaxCodeMapping,
    TaxYearRuleSet,
)


class SiiAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='sii',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(self.user)

    def _assert_transition_metadata(self, event, *, field, previous, current):
        self.assertEqual(event.metadata['campo_estado'], field)
        self.assertEqual(event.metadata['estado_anterior'], previous)
        self.assertEqual(event.metadata['estado_nuevo'], current)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='SiiCo', rut='88888888-8'):
        socio_1 = self._create_socio(f'{nombre} Socio 1', '11111111-1')
        socio_2 = self._create_socio(f'{nombre} Socio 2', '22222222-2')
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_1,
            empresa_owner=empresa,
            porcentaje='60.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_2,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        return empresa

    def _setup_paid_payment(self, with_facturadora=True, monto_facturable='100000.00', monto_cobrado='100111.00'):
        empresa = self._create_active_empresa()
        propiedad = Propiedad.objects.create(
            direccion='Av SII',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='SII-001',
            estado='activa',
            empresa_owner=empresa,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Uno',
            numero_cuenta='ACC-SII',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa if with_facturadora else None,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=with_facturadora,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario SII',
            rut='44444444-4',
            email='tenant@example.com',
            telefono='999',
            domicilio_notificaciones='Dir 123',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato='SII-CTR',
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            fecha_entrega='2026-01-01',
            dia_pago_mensual=5,
            plazo_notificacion_termino_dias=60,
            dias_prealerta_admin=90,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        periodo = PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        pago = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp=monto_facturable,
            monto_calculado_clp=monto_cobrado,
            monto_pagado_clp=monto_cobrado,
            fecha_vencimiento='2026-01-05',
            fecha_deposito_banco='2026-01-08',
            estado_pago='pagado',
            dias_mora=3,
            codigo_conciliacion_efectivo='111',
        )
        sync_payment_distribution(pago)
        return empresa, pago

    def _activate_capability(self, empresa, estado_gate='abierto', capacidad_key='DTEEmision', prefix='dte'):
        return self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': capacidad_key,
                **self._sii_readiness_fields(prefix),
                'ambiente': 'certificacion',
                'estado_gate': estado_gate,
                'ultimo_resultado': {},
            },
            format='json',
        )

    def _sii_readiness_fields(self, prefix):
        return {
            'certificado_ref': f'certificado-{prefix}-ref',
            'evidencia_ref': f'evidencia-{prefix}-gate',
            'prueba_flujo_ref': f'prueba-{prefix}-flujo',
            'autorizacion_ambiente_ref': f'ambiente-{prefix}-certificacion',
            'regla_fiscal_ref': f'regla-{prefix}-validada',
        }

    def _activate_fiscal_config(self, empresa, ddjj_habilitadas=None, *, with_tax_year_ruleset=True, anio_tributario=2027):
        regime, _ = RegimenTributarioEmpresa.objects.get_or_create(
            codigo_regimen='EmpresaContabilidadCompletaV1',
            defaults={'descripcion': 'Regimen canonico', 'estado': 'activa'},
        )
        config = ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=regime,
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=ddjj_habilitadas or [],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )
        if with_tax_year_ruleset:
            self._ensure_tax_year_ruleset(regime, anio_tributario=anio_tributario)
        return config

    def _ensure_tax_year_ruleset(self, regime, *, anio_tributario=2027):
        rule_set = TaxYearRuleSet.objects.filter(
            anio_tributario=anio_tributario,
            regimen_tributario=regime,
            estado=EstadoReglaTributariaAnual.APPROVED,
        ).first()
        if rule_set is None:
            rule_set, _ = TaxYearRuleSet.objects.get_or_create(
                anio_tributario=anio_tributario,
                regimen_tributario=regime,
                version=f'AT{anio_tributario}-controlled-v1',
                defaults={
                    'estado': EstadoReglaTributariaAnual.APPROVED,
                    'fuente_ref': f'tax-rule-source-at{anio_tributario}-controlled',
                    'hash_normativo': 'b' * 64,
                    'responsable_aprobacion_ref': f'tax-rule-reviewer-at{anio_tributario}-controlled',
                    'metadata': {'source': 'sii-test-controlled'},
                },
            )
        if rule_set.estado != EstadoReglaTributariaAnual.APPROVED:
            rule_set.estado = EstadoReglaTributariaAnual.APPROVED
            rule_set.fuente_ref = f'tax-rule-source-at{anio_tributario}-controlled'
            rule_set.hash_normativo = 'b' * 64
            rule_set.responsable_aprobacion_ref = f'tax-rule-reviewer-at{anio_tributario}-controlled'
            rule_set.save(
                update_fields=[
                    'estado',
                    'fuente_ref',
                    'hash_normativo',
                    'responsable_aprobacion_ref',
                    'updated_at',
                ]
            )
        for destino in (
            DestinoMapeoTributarioAnual.RLI,
            DestinoMapeoTributarioAnual.CPT,
            DestinoMapeoTributarioAnual.RAI,
            DestinoMapeoTributarioAnual.SAC,
            DestinoMapeoTributarioAnual.DDJJ,
            DestinoMapeoTributarioAnual.F22,
        ):
            source_metric = {
                DestinoMapeoTributarioAnual.RLI: 'monthly_tax_facts.rent_distributions_total_devengado',
                DestinoMapeoTributarioAnual.CPT: 'monthly_tax_facts.obligations_total_amount',
            }.get(destino, '')
            TaxCodeMapping.objects.get_or_create(
                rule_set=rule_set,
                destino=destino,
                codigo_interno=f'lease.{destino.lower()}.controlled',
                codigo_destino=f'{destino}-CONTROL',
                defaults={
                    'formula_ref': f'formula-ref-{destino.lower()}-controlled',
                    'evidencia_ref': f'evidence-ref-{destino.lower()}-controlled',
                    'metadata': {
                        'source': 'sii-test-controlled',
                        **({'source_metric': source_metric} if source_metric else {}),
                    },
                },
            )
        return rule_set

    def _annual_source_summary(self, fiscal_year=2026):
        return {
            'empresa_id': 1,
            'anio_comercial': fiscal_year,
            'regimen_tributario': 'EmpresaContabilidadCompletaV1',
            'moneda_funcional': 'CLP',
            'approved_close_months': list(range(1, 13)),
            'approved_closes_total': 12,
            'obligation_months': list(range(1, 13)),
            'obligations_total': 12,
            'obligations_total_amount': '120133.20',
            'obligations_by_type': ['PPM'],
            'f29_preparations_total': 0,
            'f29_traceable_months': [],
        }

    def _annual_source_hash(self, summary):
        payload = json.dumps(summary, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def test_annual_tax_source_bundle_requires_traceable_frozen_sources(self):
        empresa = self._create_active_empresa(nombre='AnnualSourceDomainCo', rut='59595959-5')
        self._activate_fiscal_config(empresa)
        incomplete_summary = {
            **self._annual_source_summary(),
            'empresa_id': empresa.id,
            'approved_close_months': list(range(1, 12)),
        }
        bundle = AnnualTaxSourceBundle(
            empresa=empresa,
            anio_tributario=2027,
            anio_comercial=2026,
            source_kind=SourceKindRentaAnual.CONTROLLED_SNAPSHOT,
            source_label='annual-source-controlled-at2027',
            authorization_ref='annual-source-authorization-at2027',
            responsible_ref='annual-source-reviewer-at2027',
            hash_fuentes=self._annual_source_hash(incomplete_summary),
            resumen_fuentes=incomplete_summary,
            estado=EstadoAnnualTaxSourceBundle.FROZEN,
        )

        with self.assertRaises(ValidationError) as incomplete_error:
            bundle.full_clean()

        self.assertIn('resumen_fuentes', incomplete_error.exception.message_dict)

        complete_summary = {**self._annual_source_summary(), 'empresa_id': empresa.id}
        bundle.resumen_fuentes = complete_summary
        bundle.hash_fuentes = 'f' * 64
        with self.assertRaises(ValidationError) as hash_error:
            bundle.full_clean()
        self.assertIn('hash_fuentes', hash_error.exception.message_dict)

        bundle.hash_fuentes = self._annual_source_hash(complete_summary)
        bundle.full_clean()
        bundle.save()
        self.assertEqual(bundle.hash_fuentes, self._annual_source_hash(complete_summary))

    def test_annual_tax_source_bundle_admin_redacts_sensitive_refs(self):
        empresa = self._create_active_empresa(nombre='AnnualSourceAdminCo', rut='60606060-6')
        self._activate_fiscal_config(empresa)
        bundle = AnnualTaxSourceBundle.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            anio_comercial=2026,
            source_kind=SourceKindRentaAnual.LOCAL,
            source_label='https://sii.example.test/source?token=secret',
            authorization_ref='Bearer authorization-secret',
            responsible_ref='https://sii.example.test/responsible?token=secret',
            resumen_fuentes={'api_key': 'secret'},
            estado=EstadoAnnualTaxSourceBundle.DRAFT,
        )
        bundle_admin = AnnualTaxSourceBundleAdmin(AnnualTaxSourceBundle, AdminSite())

        self.assertEqual(bundle_admin.source_label_redacted(bundle), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(bundle_admin.authorization_ref_redacted(bundle), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(bundle_admin.responsible_ref_redacted(bundle), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret', json.dumps(bundle_admin.resumen_fuentes_redacted(bundle)))

    def test_annual_tax_source_bundle_api_creates_and_redacts_snapshot_refs(self):
        empresa = self._create_active_empresa(nombre='AnnualSourceApiCo', rut='61616161-6')
        self._activate_fiscal_config(empresa)
        summary = {**self._annual_source_summary(), 'empresa_id': empresa.id}

        response = self.client.post(
            reverse('sii-annual-source-bundle-list'),
            {
                'empresa': empresa.id,
                'anio_tributario': 2027,
                'anio_comercial': 2026,
                'source_kind': SourceKindRentaAnual.CONTROLLED_SNAPSHOT,
                'source_label': 'annual-source-api-at2027',
                'authorization_ref': 'annual-source-api-authorization-at2027',
                'responsible_ref': 'annual-source-api-reviewer-at2027',
                'hash_fuentes': self._annual_source_hash(summary),
                'resumen_fuentes': summary,
                'estado': EstadoAnnualTaxSourceBundle.FROZEN,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        AnnualTaxSourceBundle.objects.filter(pk=response.data['id']).update(
            source_label='https://sii.example.test/source?token=secret',
            authorization_ref='Bearer authorization-secret',
            responsible_ref='https://sii.example.test/responsible?token=secret',
            resumen_fuentes={
                'api_key': 'secret',
                'approved_close_months': list(range(1, 13)),
                'obligation_months': list(range(1, 13)),
            },
        )

        snapshot = self.client.get(reverse('sii-snapshot'))
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        bundle_snapshot = next(
            item for item in snapshot.data['annual_tax_source_bundles'] if item['id'] == response.data['id']
        )
        serialized_snapshot = json.dumps(snapshot.data)
        self.assertEqual(bundle_snapshot['source_label'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(bundle_snapshot['authorization_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(bundle_snapshot['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('token=secret', serialized_snapshot)
        self.assertNotIn('authorization-secret', serialized_snapshot)

    def test_tax_year_ruleset_and_mapping_require_traceable_non_sensitive_refs(self):
        empresa = self._create_active_empresa(nombre='TaxRuleCo', rut='56565656-5')
        config = self._activate_fiscal_config(empresa)
        rule_set = TaxYearRuleSet(
            anio_tributario=2026,
            regimen_tributario=config.regimen_tributario,
            version='AT2026-v1',
            estado=EstadoReglaTributariaAnual.APPROVED,
            fuente_ref='https://sii.example.test/rule?token=secret',
            hash_normativo='bad-hash',
            responsable_aprobacion_ref='tax-reviewer-controlled',
        )

        with self.assertRaises(ValidationError) as rule_error:
            rule_set.full_clean()

        self.assertIn('fuente_ref', rule_error.exception.message_dict)
        self.assertIn('hash_normativo', rule_error.exception.message_dict)

        rule_set.fuente_ref = 'tax-rule-source-at2026-controlled'
        rule_set.hash_normativo = 'A' * 64
        rule_set.full_clean()
        rule_set.save()
        self.assertEqual(rule_set.hash_normativo, 'a' * 64)

        mapping = TaxCodeMapping(
            rule_set=rule_set,
            destino=DestinoMapeoTributarioAnual.F22,
            codigo_interno='lease.revenue.net',
            codigo_destino='F22-001',
            formula_ref='',
            evidencia_ref='https://sii.example.test/evidence?token=secret',
        )

        with self.assertRaises(ValidationError) as mapping_error:
            mapping.full_clean()

        self.assertIn('formula_ref', mapping_error.exception.message_dict)
        self.assertIn('evidencia_ref', mapping_error.exception.message_dict)

    def test_tax_year_ruleset_admin_redacts_sensitive_refs(self):
        empresa = self._create_active_empresa(nombre='TaxRuleAdminCo', rut='57575757-5')
        config = self._activate_fiscal_config(empresa)
        rule_set = TaxYearRuleSet.objects.create(
            anio_tributario=2026,
            regimen_tributario=config.regimen_tributario,
            version='AT2026-v1',
            estado=EstadoReglaTributariaAnual.DRAFT,
            fuente_ref='https://sii.example.test/rule?token=secret',
            responsable_aprobacion_ref='Bearer reviewer-secret',
            metadata={'api_key': 'secret'},
        )
        mapping = TaxCodeMapping.objects.create(
            rule_set=rule_set,
            destino=DestinoMapeoTributarioAnual.F22,
            codigo_interno='lease.revenue.net',
            codigo_destino='F22-001',
            formula_ref='https://sii.example.test/formula?token=secret',
            evidencia_ref='Bearer evidence-secret',
            metadata={'credential': 'secret'},
        )
        site = AdminSite()
        rule_admin = TaxYearRuleSetAdmin(TaxYearRuleSet, site)
        mapping_admin = TaxCodeMappingAdmin(TaxCodeMapping, site)

        self.assertEqual(rule_admin.fuente_ref_redacted(rule_set), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(rule_admin.responsable_aprobacion_ref_redacted(rule_set), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret', json.dumps(rule_admin.metadata_redacted(rule_set)))
        self.assertEqual(mapping_admin.formula_ref_redacted(mapping), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(mapping_admin.evidencia_ref_redacted(mapping), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret', json.dumps(mapping_admin.metadata_redacted(mapping)))

    def test_tax_year_ruleset_api_creates_mapping_and_redacts_snapshot_refs(self):
        empresa = self._create_active_empresa(nombre='TaxRuleApiCo', rut='58585858-5')
        config = self._activate_fiscal_config(empresa)

        rule_response = self.client.post(
            reverse('sii-tax-year-ruleset-list'),
            {
                'anio_tributario': 2026,
                'regimen_tributario': config.regimen_tributario_id,
                'version': 'AT2026-api-v1',
                'estado': EstadoReglaTributariaAnual.APPROVED,
                'fuente_ref': 'tax-rule-source-api-controlled',
                'hash_normativo': 'c' * 64,
                'responsable_aprobacion_ref': 'tax-rule-api-reviewer-controlled',
                'metadata': {'source': 'api-controlled'},
            },
            format='json',
        )
        self.assertEqual(rule_response.status_code, status.HTTP_201_CREATED)

        mapping_response = self.client.post(
            reverse('sii-tax-code-mapping-list'),
            {
                'rule_set': rule_response.data['id'],
                'destino': DestinoMapeoTributarioAnual.F22,
                'codigo_interno': 'lease.revenue.net',
                'codigo_destino': 'F22-CONTROL',
                'formula_ref': 'formula-ref-api-controlled',
                'evidencia_ref': 'evidence-ref-api-controlled',
                'metadata': {'source': 'api-controlled'},
            },
            format='json',
        )
        self.assertEqual(mapping_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(mapping_response.data['formula_ref'], 'formula-ref-api-controlled')

        TaxYearRuleSet.objects.filter(pk=rule_response.data['id']).update(
            fuente_ref='https://sii.example.test/rule?token=secret',
            responsable_aprobacion_ref='Bearer reviewer-secret',
            metadata={'api_key': 'secret'},
        )
        TaxCodeMapping.objects.filter(pk=mapping_response.data['id']).update(
            formula_ref='https://sii.example.test/formula?token=secret',
            evidencia_ref='Bearer evidence-secret',
            metadata={'credential': 'secret'},
        )

        snapshot = self.client.get(reverse('sii-snapshot'))
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        serialized_snapshot = json.dumps(snapshot.data)
        self.assertEqual(
            next(item for item in snapshot.data['tax_year_rule_sets'] if item['id'] == rule_response.data['id'])['fuente_ref'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(
            next(item for item in snapshot.data['tax_code_mappings'] if item['id'] == mapping_response.data['id'])['formula_ref'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertNotIn('token=secret', serialized_snapshot)
        self.assertNotIn('reviewer-secret', serialized_snapshot)

    def _valid_source_bundle_summary(self):
        return {
            'approved_close_months': list(range(1, 13)),
            'approved_closes_total': 12,
            'obligation_months': list(range(1, 13)),
            'obligations_total': 12,
            'f29_preparations_total': 0,
            'source_scope': 'sii-test-controlled',
        }

    def test_annual_tax_source_bundle_requires_traceable_non_sensitive_refs(self):
        empresa = self._create_active_empresa(nombre='SourceBundleCo', rut='59595959-5')
        self._activate_fiscal_config(empresa)
        bundle = AnnualTaxSourceBundle(
            empresa=empresa,
            anio_tributario=2027,
            anio_comercial=2026,
            source_kind=SourceKindRentaAnual.CONTROLLED_SNAPSHOT,
            source_label='https://sii.example.test/source?token=secret',
            authorization_ref='',
            responsible_ref='tax-source-owner-controlled',
            hash_fuentes='bad-hash',
            resumen_fuentes=self._valid_source_bundle_summary(),
            estado=EstadoAnnualTaxSourceBundle.FROZEN,
        )

        with self.assertRaises(ValidationError) as error:
            bundle.full_clean()

        self.assertIn('source_label', error.exception.message_dict)
        self.assertIn('authorization_ref', error.exception.message_dict)
        self.assertIn('hash_fuentes', error.exception.message_dict)

        bundle.source_label = 'source-bundle-at2027-controlled'
        bundle.authorization_ref = 'source-bundle-authorization-at2027'
        expected_hash = self._annual_source_hash(self._valid_source_bundle_summary())
        bundle.hash_fuentes = expected_hash.upper()
        bundle.full_clean()
        bundle.save()
        self.assertEqual(bundle.hash_fuentes, expected_hash)

    def test_annual_tax_source_bundle_admin_redacts_sensitive_refs(self):
        empresa = self._create_active_empresa(nombre='SourceBundleAdminCo', rut='60606060-6')
        self._activate_fiscal_config(empresa)
        bundle = AnnualTaxSourceBundle.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            anio_comercial=2026,
            source_kind=SourceKindRentaAnual.LOCAL,
            source_label='https://sii.example.test/source?token=secret',
            authorization_ref='Bearer source-secret',
            responsible_ref='https://sii.example.test/responsible?token=secret',
            hash_fuentes='e' * 64,
            resumen_fuentes={'api_key': 'secret'},
            estado=EstadoAnnualTaxSourceBundle.DRAFT,
        )
        site = AdminSite()
        bundle_admin = AnnualTaxSourceBundleAdmin(AnnualTaxSourceBundle, site)

        self.assertEqual(bundle_admin.source_label_redacted(bundle), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(bundle_admin.authorization_ref_redacted(bundle), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(bundle_admin.responsible_ref_redacted(bundle), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret', json.dumps(bundle_admin.resumen_fuentes_redacted(bundle)))

    def test_annual_tax_source_bundle_api_creates_and_snapshot_redacts_refs(self):
        empresa = self._create_active_empresa(nombre='SourceBundleApiCo', rut='61616161-6')
        self._activate_fiscal_config(empresa)
        summary = self._valid_source_bundle_summary()

        response = self.client.post(
            reverse('sii-annual-source-bundle-list'),
            {
                'empresa': empresa.id,
                'anio_tributario': 2027,
                'anio_comercial': 2026,
                'source_kind': SourceKindRentaAnual.LOCAL,
                'source_label': 'source-bundle-api-controlled',
                'authorization_ref': '',
                'responsible_ref': 'source-bundle-api-owner',
                'hash_fuentes': self._annual_source_hash(summary),
                'resumen_fuentes': summary,
                'estado': EstadoAnnualTaxSourceBundle.FROZEN,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['source_label'], 'source-bundle-api-controlled')
        AnnualTaxSourceBundle.objects.filter(pk=response.data['id']).update(
            source_label='https://sii.example.test/source?token=secret',
            authorization_ref='Bearer source-secret',
            responsible_ref='https://sii.example.test/responsible?token=secret',
            resumen_fuentes={'credential': 'secret'},
        )

        snapshot = self.client.get(reverse('sii-snapshot'))
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        source_bundle = next(
            item for item in snapshot.data['annual_tax_source_bundles'] if item['id'] == response.data['id']
        )
        serialized_snapshot = json.dumps(snapshot.data)
        self.assertEqual(source_bundle['source_label'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(source_bundle['authorization_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(source_bundle['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('token=secret', serialized_snapshot)
        self.assertNotIn('source-secret', serialized_snapshot)

    def test_annual_tax_source_bundle_api_rejects_update_when_frozen(self):
        empresa = self._create_active_empresa(nombre='SourceBundleFrozenApiCo', rut='62626262-6')
        self._activate_fiscal_config(empresa)
        summary = self._valid_source_bundle_summary()
        bundle = AnnualTaxSourceBundle.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            anio_comercial=2026,
            source_kind=SourceKindRentaAnual.LOCAL,
            source_label='source-bundle-frozen-controlled',
            responsible_ref='source-bundle-frozen-owner',
            hash_fuentes=self._annual_source_hash(summary),
            resumen_fuentes=summary,
            estado=EstadoAnnualTaxSourceBundle.FROZEN,
        )

        response = self.client.patch(
            reverse('sii-annual-source-bundle-detail', args=[bundle.id]),
            {'source_label': 'source-bundle-mutated'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)

    def _create_monthly_close_and_obligation(self, empresa, estado_preparacion='preparado'):
        close = CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='aprobado',
        )
        obligation = ObligacionTributariaMensual.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible='100111.00',
            monto_calculado='10011.10',
            estado_preparacion=estado_preparacion,
        )
        return close, obligation

    def _create_twelve_approved_closes(self, empresa, fiscal_year=2026):
        for month in range(1, 13):
            CierreMensualContable.objects.create(
                empresa=empresa,
                anio=fiscal_year,
                mes=month,
                estado='aprobado',
            )
            ObligacionTributariaMensual.objects.create(
                empresa=empresa,
                anio=fiscal_year,
                mes=month,
                obligacion_tipo='PPM',
                base_imponible='100111.00',
                monto_calculado='10011.10',
                estado_preparacion='preparado',
            )

    def _activate_annual_capabilities(self, empresa):
        for capability_key in ('DDJJPreparacion', 'F22Preparacion'):
            response = self.client.post(
                reverse('sii-capacidad-list'),
                {
                    'empresa': empresa.id,
                    'capacidad_key': capability_key,
                    **self._sii_readiness_fields(capability_key.lower()),
                    'ambiente': 'certificacion',
                    'estado_gate': 'abierto',
                    'ultimo_resultado': {},
                },
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_auth_is_required_for_sii_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('sii-capacidad-list'),
            reverse('sii-dte-list'),
            reverse('sii-dte-generate'),
            reverse('sii-annual-source-bundle-list'),
        ]
        for url in urls:
            response = client.get(url) if 'generar' not in url else client.post(url, {}, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_generate_dte_draft_requires_capability_and_fiscal_setup(self):
        empresa, pago = self._setup_paid_payment()
        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self._activate_fiscal_config(empresa)
        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self._activate_capability(empresa)
        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_sii_capability_create_rolls_back_when_view_audit_fails(self):
        empresa = self._create_active_empresa(nombre='SII Audit Create SpA', rut='38383838-3')
        self._activate_fiscal_config(empresa)
        audit_count = AuditEvent.objects.count()

        with patch('sii.views.create_audit_event', side_effect=RuntimeError('sii capability audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'sii capability audit unavailable'):
                self.client.post(
                    reverse('sii-capacidad-list'),
                    {
                        'empresa': empresa.id,
                        'capacidad_key': 'DTEEmision',
                        **self._sii_readiness_fields('dte-audit-create'),
                        'ambiente': 'certificacion',
                        'estado_gate': 'abierto',
                        'ultimo_resultado': {},
                    },
                    format='json',
                )

        self.assertFalse(
            CapacidadTributariaSII.objects.filter(empresa=empresa, capacidad_key='DTEEmision').exists()
        )
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_sii_capability_update_rolls_back_when_state_audit_fails(self):
        from audit.services import create_audit_event as real_create_audit_event

        empresa = self._create_active_empresa(nombre='SII Audit Update SpA', rut='39393939-3')
        self._activate_fiscal_config(empresa)
        created = self._activate_capability(empresa)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        audit_count = AuditEvent.objects.count()

        def fail_state_change_audit(**kwargs):
            if kwargs.get('event_type') == 'sii.capacidad_sii.state_changed':
                raise RuntimeError('sii capability state audit unavailable')
            return real_create_audit_event(**kwargs)

        with patch('sii.views.create_audit_event', side_effect=fail_state_change_audit):
            with self.assertRaisesRegex(RuntimeError, 'sii capability state audit unavailable'):
                self.client.patch(
                    reverse('sii-capacidad-detail', args=[created.data['id']]),
                    {'estado_gate': 'condicionado'},
                    format='json',
                )

        stored = CapacidadTributariaSII.objects.get(pk=created.data['id'])
        self.assertEqual(stored.estado_gate, 'abierto')
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_sii_capability_state_change_audit_includes_metadata(self):
        empresa = self._create_active_empresa(nombre='SII Audit Metadata SpA', rut='39393939-4')
        self._activate_fiscal_config(empresa)
        created = self._activate_capability(empresa)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        response = self.client.patch(
            reverse('sii-capacidad-detail', args=[created.data['id']]),
            {'estado_gate': 'condicionado'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = AuditEvent.objects.get(
            event_type='sii.capacidad_sii.state_changed',
            entity_type='capacidad_sii',
            entity_id=str(created.data['id']),
        )
        self._assert_transition_metadata(
            event,
            field='estado_gate',
            previous='abierto',
            current='condicionado',
        )

    def test_sii_operational_refs_normalize_before_full_clean_and_save(self):
        def sized_ref(prefix, size, fill):
            return prefix + (fill * (size - len(prefix)))

        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        distribution = pago.distribuciones_cobro.get()

        certificate_ref = sized_ref('sii-cap-cert-', 255, 'c')
        evidence_ref = sized_ref('sii-cap-evidence-', 255, 'e')
        flow_ref = sized_ref('sii-cap-flow-', 255, 'f')
        environment_ref = sized_ref('sii-cap-env-', 255, 'a')
        fiscal_rule_ref = sized_ref('sii-cap-rule-', 255, 'r')

        dte_capability = CapacidadTributariaSII(
            empresa=empresa,
            capacidad_key='DTEEmision',
            certificado_ref=f'   {certificate_ref}   ',
            evidencia_ref=f'   {evidence_ref}   ',
            prueba_flujo_ref=f'   {flow_ref}   ',
            autorizacion_ambiente_ref=f'   {environment_ref}   ',
            regla_fiscal_ref=f'   {fiscal_rule_ref}   ',
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        dte_capability.full_clean()
        self.assertEqual(dte_capability.certificado_ref, certificate_ref)
        self.assertEqual(dte_capability.evidencia_ref, evidence_ref)
        self.assertEqual(dte_capability.prueba_flujo_ref, flow_ref)
        self.assertEqual(dte_capability.autorizacion_ambiente_ref, environment_ref)
        self.assertEqual(dte_capability.regla_fiscal_ref, fiscal_rule_ref)
        dte_capability.save()
        stored_capability = CapacidadTributariaSII.objects.get(pk=dte_capability.pk)
        self.assertEqual(stored_capability.certificado_ref, certificate_ref)
        self.assertEqual(stored_capability.evidencia_ref, evidence_ref)

        dte_track_ref = sized_ref('dte-track-', 64, 't')
        dte_state = sized_ref('dte-state-', 128, 's')
        dte = DTEEmitido(
            empresa=empresa,
            capacidad_tributaria=dte_capability,
            contrato=pago.contrato,
            pago_mensual=pago,
            distribucion_cobro_mensual=distribution,
            arrendatario=pago.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision='2026-01-08',
            sii_track_id=f'   {dte_track_ref}   ',
            ultimo_estado_sii=f'   {dte_state}   ',
            observaciones='   observacion tributaria controlada   ',
        )
        dte.full_clean()
        self.assertEqual(dte.sii_track_id, dte_track_ref)
        self.assertEqual(dte.ultimo_estado_sii, dte_state)
        self.assertEqual(dte.observaciones, 'observacion tributaria controlada')
        dte.save()
        stored_dte = DTEEmitido.objects.get(pk=dte.pk)
        self.assertEqual(stored_dte.sii_track_id, dte_track_ref)
        self.assertEqual(stored_dte.ultimo_estado_sii, dte_state)
        self.assertEqual(stored_dte.observaciones, 'observacion tributaria controlada')

        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29-full-clean'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        f29_ref = sized_ref('f29-draft-', 255, 'f')
        f29_responsible_ref = sized_ref('f29-review-', 255, 'r')
        f29 = F29PreparacionMensual(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='aprobado_para_presentacion',
            resumen_formulario={'source': 'controlled'},
            borrador_ref=f'   {f29_ref}   ',
            responsable_revision_ref=f'   {f29_responsible_ref}   ',
            observaciones='   f29 listo para revision   ',
        )
        f29.full_clean()
        self.assertEqual(f29.borrador_ref, f29_ref)
        self.assertEqual(f29.responsable_revision_ref, f29_responsible_ref)
        self.assertEqual(f29.observaciones, 'f29 listo para revision')
        f29.save()
        stored_f29 = F29PreparacionMensual.objects.get(pk=f29.pk)
        self.assertEqual(stored_f29.borrador_ref, f29_ref)
        self.assertEqual(stored_f29.responsable_revision_ref, f29_responsible_ref)
        self.assertEqual(stored_f29.observaciones, 'f29 listo para revision')

        process_ddjj_ref = sized_ref('annual-ddjj-', 255, 'd')
        process_f22_ref = sized_ref('annual-f22-', 255, 'z')
        process_responsible_ref = sized_ref('annual-review-', 255, 'r')
        process = ProcesoRentaAnual(
            empresa=empresa,
            anio_tributario=2027,
            estado='aprobado_para_presentacion',
            resumen_anual={'source': 'controlled'},
            paquete_ddjj_ref=f'   {process_ddjj_ref}   ',
            borrador_f22_ref=f'   {process_f22_ref}   ',
            responsable_revision_ref=f'   {process_responsible_ref}   ',
        )
        process.full_clean()
        self.assertEqual(process.paquete_ddjj_ref, process_ddjj_ref)
        self.assertEqual(process.borrador_f22_ref, process_f22_ref)
        self.assertEqual(process.responsable_revision_ref, process_responsible_ref)
        process.save()
        stored_process = ProcesoRentaAnual.objects.get(pk=process.pk)
        self.assertEqual(stored_process.paquete_ddjj_ref, process_ddjj_ref)
        self.assertEqual(stored_process.borrador_f22_ref, process_f22_ref)
        self.assertEqual(stored_process.responsable_revision_ref, process_responsible_ref)

        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj-full-clean'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22-full-clean'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        ddjj_ref = sized_ref('ddjj-package-', 255, 'j')
        ddjj_responsible_ref = sized_ref('ddjj-review-', 255, 'j')
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_paquete={'source': 'controlled'},
            paquete_ref=f'   {ddjj_ref}   ',
            responsable_revision_ref=f'   {ddjj_responsible_ref}   ',
            observaciones='   paquete ddjj preparado   ',
        )
        ddjj.full_clean()
        self.assertEqual(ddjj.paquete_ref, ddjj_ref)
        self.assertEqual(ddjj.responsable_revision_ref, ddjj_responsible_ref)
        self.assertEqual(ddjj.observaciones, 'paquete ddjj preparado')
        ddjj.save()
        stored_ddjj = DDJJPreparacionAnual.objects.get(pk=ddjj.pk)
        self.assertEqual(stored_ddjj.paquete_ref, ddjj_ref)
        self.assertEqual(stored_ddjj.responsable_revision_ref, ddjj_responsible_ref)
        self.assertEqual(stored_ddjj.observaciones, 'paquete ddjj preparado')

        f22_ref = sized_ref('f22-draft-', 255, 'b')
        f22_responsible_ref = sized_ref('f22-review-', 255, 'b')
        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_f22={'source': 'controlled'},
            borrador_ref=f'   {f22_ref}   ',
            responsable_revision_ref=f'   {f22_responsible_ref}   ',
            observaciones='   f22 preparado   ',
        )
        f22.full_clean()
        self.assertEqual(f22.borrador_ref, f22_ref)
        self.assertEqual(f22.responsable_revision_ref, f22_responsible_ref)
        self.assertEqual(f22.observaciones, 'f22 preparado')
        f22.save()
        stored_f22 = F22PreparacionAnual.objects.get(pk=f22.pk)
        self.assertEqual(stored_f22.borrador_ref, f22_ref)
        self.assertEqual(stored_f22.responsable_revision_ref, f22_responsible_ref)
        self.assertEqual(stored_f22.observaciones, 'f22 preparado')

    def test_generate_dte_draft_rolls_back_when_view_audit_fails(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)
        audit_count = AuditEvent.objects.count()

        with patch('sii.views.create_audit_event', side_effect=RuntimeError('dte draft audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'dte draft audit unavailable'):
                self.client.post(
                    reverse('sii-dte-generate'),
                    {'pago_mensual_id': pago.id},
                    format='json',
                )

        self.assertFalse(DTEEmitido.objects.filter(pago_mensual=pago).exists())
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_update_dte_status_rolls_back_when_view_audit_fails(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        audit_count = AuditEvent.objects.count()

        with patch('sii.views.create_audit_event', side_effect=RuntimeError('dte status audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'dte status audit unavailable'):
                self.client.post(
                    reverse('sii-dte-status', args=[generated.data['id']]),
                    {
                        'estado_dte': 'enviado_manual_controlado',
                        'sii_track_id': '0245399452',
                        'ultimo_estado_sii': 'Recibido',
                    },
                    format='json',
                )

        stored = DTEEmitido.objects.get(pk=generated.data['id'])
        self.assertEqual(stored.estado_dte, 'borrador')
        self.assertEqual(stored.sii_track_id, '')
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_generate_f29_draft_rolls_back_when_view_audit_fails(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, capacidad_key='F29Preparacion', prefix='f29-audit')
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        audit_count = AuditEvent.objects.count()

        with patch('sii.views.create_audit_event', side_effect=RuntimeError('f29 draft audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'f29 draft audit unavailable'):
                self.client.post(
                    reverse('sii-f29-generate'),
                    {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
                    format='json',
                )

        self.assertFalse(F29PreparacionMensual.objects.filter(empresa=empresa, anio=2026, mes=1).exists())
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_update_f29_status_rolls_back_when_view_audit_fails(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, capacidad_key='F29Preparacion', prefix='f29-audit-status')
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        generated = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        audit_count = AuditEvent.objects.count()

        with patch('sii.views.create_audit_event', side_effect=RuntimeError('f29 status audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'f29 status audit unavailable'):
                self.client.post(
                    reverse('sii-f29-status', args=[generated.data['id']]),
                    {
                        'estado_preparacion': 'aprobado_para_presentacion',
                        'borrador_ref': 'f29-2026-01',
                        'responsable_revision_ref': 'tax-reviewer-f29-2026-01',
                    },
                    format='json',
                )

        stored = F29PreparacionMensual.objects.get(pk=generated.data['id'])
        self.assertEqual(stored.estado_preparacion, 'preparado')
        self.assertEqual(stored.borrador_ref, '')
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_generate_annual_preparation_rolls_back_when_view_audit_fails(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        audit_count = AuditEvent.objects.count()

        with patch('sii.views.create_audit_event', side_effect=RuntimeError('annual preparation audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'annual preparation audit unavailable'):
                self.client.post(
                    reverse('sii-anual-generate'),
                    {'empresa_id': empresa.id, 'anio_tributario': 2027},
                    format='json',
                )

        self.assertFalse(ProcesoRentaAnual.objects.filter(empresa=empresa, anio_tributario=2027).exists())
        self.assertFalse(DDJJPreparacionAnual.objects.filter(empresa=empresa, anio_tributario=2027).exists())
        self.assertFalse(F22PreparacionAnual.objects.filter(empresa=empresa, anio_tributario=2027).exists())
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_update_annual_status_rolls_back_when_view_audit_fails(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        audit_count = AuditEvent.objects.count()

        with patch('sii.views.create_audit_event', side_effect=RuntimeError('annual status audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'annual status audit unavailable'):
                self.client.post(
                    reverse('sii-ddjj-status', args=[generated.data['ddjj_preparacion']['id']]),
                    {
                        'estado_preparacion': 'aprobado_para_presentacion',
                        'ref_value': 'ddjj-2027',
                        'responsable_revision_ref': 'tax-reviewer-ddjj-2027',
                        'observaciones': 'Paquete DDJJ listo.',
                    },
                    format='json',
                )

        process = ProcesoRentaAnual.objects.get(pk=generated.data['proceso_renta_anual']['id'])
        ddjj = DDJJPreparacionAnual.objects.get(pk=generated.data['ddjj_preparacion']['id'])
        self.assertEqual(process.paquete_ddjj_ref, '')
        self.assertEqual(ddjj.estado_preparacion, 'preparado')
        self.assertEqual(ddjj.paquete_ref, '')
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_tax_artifacts_reject_wrong_sii_capability_kind(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        wrong_f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('wrong-f29'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        wrong_dte_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            **self._sii_readiness_fields('wrong-dte'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        distribution = pago.distribuciones_cobro.get()
        dte = DTEEmitido(
            empresa=empresa,
            capacidad_tributaria=wrong_f29_capability,
            contrato=pago.contrato,
            pago_mensual=pago,
            distribucion_cobro_mensual=distribution,
            arrendatario=pago.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision='2026-01-08',
        )
        with self.assertRaisesMessage(ValidationError, 'DTEEmision'):
            dte.full_clean()

        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        f29 = F29PreparacionMensual(
            empresa=empresa,
            capacidad_tributaria=wrong_dte_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='preparado',
            resumen_formulario={'obligaciones': [{'tipo': 'PPM'}]},
        )
        with self.assertRaisesMessage(ValidationError, 'F29Preparacion'):
            f29.full_clean()

        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'source': 'controlled'},
        )
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'source': 'controlled'},
        )
        with self.assertRaisesMessage(ValidationError, 'DDJJPreparacion'):
            ddjj.full_clean()

        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'source': 'controlled'},
        )
        with self.assertRaisesMessage(ValidationError, 'F22Preparacion'):
            f22.full_clean()

    def test_annual_tax_payloads_require_expected_commercial_year(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        wrong_summary = {
            'fiscal_year': 2025,
            'obligaciones': [{'anio': 2025, 'mes': 1, 'tipo': 'PPM'}],
        }

        process = ProcesoRentaAnual(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual=wrong_summary,
        )
        with self.assertRaises(ValidationError) as process_error:
            process.full_clean()
        self.assertIn('resumen_anual', process_error.exception.message_dict)

        stored_process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'anio': 2026, 'mes': 1, 'tipo': 'PPM'}]},
        )
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'resumen_anual': wrong_summary},
        )
        with self.assertRaises(ValidationError) as ddjj_error:
            ddjj.full_clean()
        self.assertIn('resumen_paquete', ddjj_error.exception.message_dict)

        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'resumen_anual': wrong_summary},
        )
        with self.assertRaises(ValidationError) as f22_error:
            f22.full_clean()
        self.assertIn('resumen_f22', f22_error.exception.message_dict)

    def test_tax_payloads_reject_sensitive_keys(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')

        f29 = F29PreparacionMensual(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='preparado',
            resumen_formulario={'api_key': None},
        )
        with self.assertRaises(ValidationError) as f29_error:
            f29.full_clean()
        self.assertIn('resumen_formulario', f29_error.exception.message_dict)

        process = ProcesoRentaAnual(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'access_token': None},
        )
        with self.assertRaises(ValidationError) as process_error:
            process.full_clean()
        self.assertIn('resumen_anual', process_error.exception.message_dict)

        stored_process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'source': 'controlled'},
        )
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'resumen_anual': {'fiscal_year': 2026}, 'credential': None},
        )
        with self.assertRaises(ValidationError) as ddjj_error:
            ddjj.full_clean()
        self.assertIn('resumen_paquete', ddjj_error.exception.message_dict)

        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'resumen_anual': {'fiscal_year': 2026}, 'secret': None},
        )
        with self.assertRaises(ValidationError) as f22_error:
            f22.full_clean()
        self.assertIn('resumen_f22', f22_error.exception.message_dict)

    def test_tax_artifacts_require_traceable_ref_for_advanced_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )

        f29 = F29PreparacionMensual(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='aprobado_para_presentacion',
            resumen_formulario={'obligaciones': [{'tipo': 'PPM'}]},
        )
        with self.assertRaises(ValidationError) as f29_error:
            f29.full_clean()
        self.assertIn('borrador_ref', f29_error.exception.message_dict)

        process = ProcesoRentaAnual(
            empresa=empresa,
            anio_tributario=2027,
            estado='aprobado_para_presentacion',
            resumen_anual={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as process_error:
            process.full_clean()
        self.assertIn('paquete_ddjj_ref', process_error.exception.message_dict)
        self.assertIn('borrador_f22_ref', process_error.exception.message_dict)

        prepared_process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'source': 'controlled'},
        )
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=prepared_process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_paquete={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as ddjj_error:
            ddjj.full_clean()
        self.assertIn('paquete_ref', ddjj_error.exception.message_dict)

        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=prepared_process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_f22={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as f22_error:
            f22.full_clean()
        self.assertIn('borrador_ref', f22_error.exception.message_dict)

    def test_tax_artifacts_require_active_fiscal_config(self):
        empresa, pago = self._setup_paid_payment()
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        dte_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            **self._sii_readiness_fields('dte-no-fiscal'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29-no-fiscal'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj-no-fiscal'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22-no-fiscal'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        distribution = pago.distribuciones_cobro.get()
        dte = DTEEmitido(
            empresa=empresa,
            capacidad_tributaria=dte_capability,
            contrato=pago.contrato,
            pago_mensual=pago,
            distribucion_cobro_mensual=distribution,
            arrendatario=pago.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision='2026-01-08',
        )
        with self.assertRaises(ValidationError) as dte_error:
            dte.full_clean()
        self.assertIn('empresa', dte_error.exception.message_dict)

        f29 = F29PreparacionMensual(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='preparado',
            resumen_formulario={'obligaciones': [{'tipo': 'PPM'}]},
        )
        with self.assertRaises(ValidationError) as f29_error:
            f29.full_clean()
        self.assertIn('empresa', f29_error.exception.message_dict)

        process = ProcesoRentaAnual(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as process_error:
            process.full_clean()
        self.assertIn('empresa', process_error.exception.message_dict)

        stored_process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'source': 'controlled'},
        )
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as ddjj_error:
            ddjj.full_clean()
        self.assertIn('empresa', ddjj_error.exception.message_dict)

        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as f22_error:
            f22.full_clean()
        self.assertIn('empresa', f22_error.exception.message_dict)

    def test_open_sii_capability_requires_readiness_references(self):
        empresa = self._create_active_empresa()

        response = self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'DTEEmision',
                'certificado_ref': 'certificado-sii-ref',
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_ref', response.data)
        self.assertIn('prueba_flujo_ref', response.data)
        self.assertIn('regla_fiscal_ref', response.data)

        self._activate_fiscal_config(empresa)
        response = self._activate_capability(empresa)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_open_sii_capability_rejects_sensitive_references(self):
        empresa = self._create_active_empresa()

        response = self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'DTEEmision',
                **self._sii_readiness_fields('dte'),
                'certificado_ref': 'https://sii.example.test/cert?token=secret',
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('certificado_ref', response.data)

        response = self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'produccion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {
                    'autorizacion_produccion_ref': 'prod-auth-safe',
                    'api_key': None,
                },
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ultimo_resultado', response.data)

    def test_open_sii_capability_rejects_unsupported_fiscal_regime(self):
        empresa = self._create_active_empresa(nombre='SII Unsupported Regime SpA', rut='33333333-3')
        unsupported_regime = RegimenTributarioEmpresa.objects.create(
            codigo_regimen='RentaPresuntaV1',
            descripcion='Regimen no automatizable en v1',
            estado='activa',
        )
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=unsupported_regime,
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=[],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )

        response = self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'DTEEmision',
                **self._sii_readiness_fields('unsupported-regime'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('empresa', response.data)

    def test_open_sii_capability_requires_active_fiscal_config(self):
        empresa = self._create_active_empresa(nombre='SII No Fiscal Config SpA', rut='34343434-3')

        response = self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'DTEEmision',
                **self._sii_readiness_fields('missing-fiscal-config'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('empresa', response.data)

    def test_sii_apis_redact_inherited_sensitive_references(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        dte_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            certificado_ref='https://sii.example.test/cert?token=secret',
            evidencia_ref='https://sii.example.test/evidence?token=secret',
            prueba_flujo_ref='https://sii.example.test/flow?token=secret',
            autorizacion_ambiente_ref='https://sii.example.test/env?token=secret',
            regla_fiscal_ref='https://sii.example.test/rule?token=secret',
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={'access_token': 'opaque-token-value', 'safe_ref': 'controlled-result'},
        )
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        distribution = pago.distribuciones_cobro.get()
        dte = DTEEmitido.objects.create(
            empresa=empresa,
            capacidad_tributaria=dte_capability,
            contrato=pago.contrato,
            pago_mensual=pago,
            distribucion_cobro_mensual=distribution,
            arrendatario=pago.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision='2026-01-08',
            estado_dte='aceptado',
            sii_track_id='https://sii.example.test/track?token=secret',
            ultimo_estado_sii='Aceptado controlado',
            observaciones='Observacion con https://sii.example.test/obs?token=secret',
        )
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        f29 = F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='aprobado_para_presentacion',
            resumen_formulario={'callback': 'https://sii.example.test/f29?token=secret'},
            borrador_ref='https://sii.example.test/f29?token=secret',
            observaciones='Observacion con https://sii.example.test/f29?token=secret',
        )
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'callback': 'https://sii.example.test/anual?token=secret'},
            paquete_ddjj_ref='https://sii.example.test/ddjj?token=secret',
            borrador_f22_ref='https://sii.example.test/f22?token=secret',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_paquete={'api_key': 'secret-api-key-value'},
            paquete_ref='https://sii.example.test/ddjj?token=secret',
            observaciones='Observacion con https://sii.example.test/ddjj?token=secret',
        )
        f22 = F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_f22={'access_token': 'secret-f22-token-value'},
            borrador_ref='https://sii.example.test/f22?token=secret',
            observaciones='Observacion con https://sii.example.test/f22?token=secret',
        )

        capabilities = self.client.get(reverse('sii-capacidad-list'))
        capability_detail = self.client.get(reverse('sii-capacidad-detail', args=[dte_capability.id]))
        dtes = self.client.get(reverse('sii-dte-list'))
        dte_detail = self.client.get(reverse('sii-dte-detail', args=[dte.id]))
        f29s = self.client.get(reverse('sii-f29-list'))
        f29_detail = self.client.get(reverse('sii-f29-detail', args=[f29.id]))
        annual = self.client.get(reverse('sii-anual-list'))
        ddjjs = self.client.get(reverse('sii-ddjj-list'))
        f22s = self.client.get(reverse('sii-f22-list'))
        snapshot = self.client.get(reverse('sii-snapshot'))

        capability_data = next(item for item in capabilities.data if item['id'] == dte_capability.id)
        self.assertEqual(capability_data['certificado_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(capability_data['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(capability_data['ultimo_resultado']['access_token'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(capability_data['ultimo_resultado']['safe_ref'], 'controlled-result')
        self.assertEqual(capability_detail.data['regla_fiscal_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(dtes.data[0]['sii_track_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(dtes.data[0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(dte_detail.data['sii_track_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(dte_detail.data['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29s.data[0]['borrador_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29s.data[0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29_detail.data['resumen_formulario']['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29_detail.data['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        process_data = next(item for item in annual.data if item['id'] == process.id)
        self.assertEqual(process_data['paquete_ddjj_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(process_data['resumen_anual']['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(ddjjs.data[0]['paquete_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(ddjjs.data[0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(ddjjs.data[0]['resumen_paquete']['api_key'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f22s.data[0]['borrador_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f22s.data[0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f22s.data[0]['resumen_f22']['access_token'], REDACTED_SENSITIVE_REFERENCE)
        snapshot_capability = next(item for item in snapshot.data['capacidades'] if item['id'] == dte_capability.id)
        self.assertEqual(snapshot_capability['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['dtes'][0]['sii_track_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['dtes'][0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['f29s'][0]['borrador_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['f29s'][0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['ddjjs'][0]['paquete_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['ddjjs'][0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['f22s'][0]['borrador_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['f22s'][0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)

        body = b''.join(
            response.content
            for response in [capabilities, capability_detail, dtes, dte_detail, f29s, f29_detail, annual, ddjjs, f22s, snapshot]
        ).decode()
        self.assertNotIn('sii.example.test', body)
        self.assertNotIn('opaque-token-value', body)
        self.assertNotIn('secret-api-key-value', body)
        self.assertEqual(ddjj.estado_preparacion, 'aprobado_para_presentacion')
        self.assertEqual(f22.estado_preparacion, 'aprobado_para_presentacion')

    def test_sii_admin_redacts_sensitive_tax_refs_and_payloads(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        dte_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            certificado_ref='https://sii.example.test/cert?token=secret',
            evidencia_ref='https://sii.example.test/evidence?token=secret',
            prueba_flujo_ref='https://sii.example.test/flow?token=secret',
            autorizacion_ambiente_ref='https://sii.example.test/env?token=secret',
            regla_fiscal_ref='https://sii.example.test/rule?token=secret',
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={'access_token': 'opaque-token-value', 'safe_ref': 'controlled-result'},
        )
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        distribution = pago.distribuciones_cobro.get()
        dte = DTEEmitido.objects.create(
            empresa=empresa,
            capacidad_tributaria=dte_capability,
            contrato=pago.contrato,
            pago_mensual=pago,
            distribucion_cobro_mensual=distribution,
            arrendatario=pago.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision='2026-01-08',
            estado_dte='aceptado',
            sii_track_id='https://sii.example.test/track?token=secret',
            ultimo_estado_sii='Aceptado controlado',
            observaciones='Observacion con https://sii.example.test/obs?token=secret',
        )
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        f29 = F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='aprobado_para_presentacion',
            resumen_formulario={'callback': 'https://sii.example.test/f29?token=secret'},
            borrador_ref='https://sii.example.test/f29?token=secret',
            observaciones='Observacion con https://sii.example.test/f29?token=secret',
        )
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'callback': 'https://sii.example.test/anual?token=secret'},
            paquete_ddjj_ref='https://sii.example.test/ddjj?token=secret',
            borrador_f22_ref='https://sii.example.test/f22?token=secret',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_paquete={'api_key': 'secret-api-key-value'},
            paquete_ref='https://sii.example.test/ddjj?token=secret',
            observaciones='Observacion con https://sii.example.test/ddjj?token=secret',
        )
        f22 = F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_f22={'access_token': 'secret-f22-token-value'},
            borrador_ref='https://sii.example.test/f22?token=secret',
            observaciones='Observacion con https://sii.example.test/f22?token=secret',
        )
        site = AdminSite()

        capability_admin = CapacidadTributariaSIIAdmin(CapacidadTributariaSII, site)
        dte_admin = DTEEmitidoAdmin(DTEEmitido, site)
        f29_admin = F29PreparacionMensualAdmin(F29PreparacionMensual, site)
        process_admin = ProcesoRentaAnualAdmin(ProcesoRentaAnual, site)
        ddjj_admin = DDJJPreparacionAnualAdmin(DDJJPreparacionAnual, site)
        f22_admin = F22PreparacionAnualAdmin(F22PreparacionAnual, site)

        for raw_field in (
            'certificado_ref',
            'evidencia_ref',
            'prueba_flujo_ref',
            'autorizacion_ambiente_ref',
            'regla_fiscal_ref',
            'ultimo_resultado',
        ):
            self.assertNotIn(raw_field, capability_admin.fields)
            self.assertNotIn(raw_field, capability_admin.search_fields)
        self.assertEqual(capability_admin.certificado_ref_redacted(dte_capability), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(capability_admin.evidencia_ref_redacted(dte_capability), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(capability_admin.prueba_flujo_ref_redacted(dte_capability), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            capability_admin.autorizacion_ambiente_ref_redacted(dte_capability),
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(capability_admin.regla_fiscal_ref_redacted(dte_capability), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            capability_admin.ultimo_resultado_redacted(dte_capability)['access_token'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(capability_admin.ultimo_resultado_redacted(dte_capability)['safe_ref'], 'controlled-result')

        self.assertNotIn('sii_track_id', dte_admin.fields)
        self.assertNotIn('observaciones', dte_admin.fields)
        self.assertNotIn('sii_track_id', dte_admin.search_fields)
        self.assertEqual(dte_admin.sii_track_id_redacted(dte), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(dte_admin.observaciones_redacted(dte), REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('resumen_formulario', f29_admin.fields)
        self.assertNotIn('borrador_ref', f29_admin.fields)
        self.assertNotIn('observaciones', f29_admin.fields)
        self.assertEqual(f29_admin.resumen_formulario_redacted(f29)['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29_admin.borrador_ref_redacted(f29), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29_admin.observaciones_redacted(f29), REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('resumen_anual', process_admin.fields)
        self.assertNotIn('paquete_ddjj_ref', process_admin.fields)
        self.assertNotIn('borrador_f22_ref', process_admin.fields)
        self.assertEqual(process_admin.resumen_anual_redacted(process)['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(process_admin.paquete_ddjj_ref_redacted(process), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(process_admin.borrador_f22_ref_redacted(process), REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('resumen_paquete', ddjj_admin.fields)
        self.assertNotIn('paquete_ref', ddjj_admin.fields)
        self.assertEqual(ddjj_admin.resumen_paquete_redacted(ddjj)['api_key'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(ddjj_admin.paquete_ref_redacted(ddjj), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(ddjj_admin.observaciones_redacted(ddjj), REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('resumen_f22', f22_admin.fields)
        self.assertNotIn('borrador_ref', f22_admin.fields)
        self.assertEqual(f22_admin.resumen_f22_redacted(f22)['access_token'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f22_admin.borrador_ref_redacted(f22), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f22_admin.observaciones_redacted(f22), REDACTED_SENSITIVE_REFERENCE)

        admin_objects = (
            (capability_admin, dte_capability),
            (dte_admin, dte),
            (f29_admin, f29),
            (process_admin, process),
            (ddjj_admin, ddjj),
            (f22_admin, f22),
        )
        for model_admin, obj in admin_objects:
            self.assertEqual(set(model_admin.readonly_fields), set(model_admin.fields))
            self.assertFalse(model_admin.has_add_permission(None))
            self.assertFalse(model_admin.has_change_permission(None, obj))
            self.assertFalse(model_admin.has_delete_permission(None, obj))

    def test_generate_dte_draft_rejects_conditioned_gate(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='condicionado')

        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_dte_draft_rechecks_readiness_refs(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            certificado_ref='cert-directo',
            ambiente='certificacion',
            estado_gate='abierto',
        )

        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('readiness SII', response.data['detail'])

    def test_generate_dte_draft_uses_facturable_amount_not_coded_amount(self):
        empresa, pago = self._setup_paid_payment(monto_facturable='100000.00', monto_cobrado='100111.00')
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)

        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['monto_neto_clp'], '100000.00')
        self.assertIsNotNone(response.data['distribucion_cobro_mensual'])
        self.assertEqual(response.data['estado_dte'], 'borrador')

    def test_generate_dte_draft_is_idempotent(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)

        first = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        second = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(DTEEmitido.objects.filter(pago_mensual=pago).count(), 1)

    def test_generate_dte_draft_rejects_missing_facturadora(self):
        empresa, pago = self._setup_paid_payment(with_facturadora=False)
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)

        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_dte_draft_only_allows_factura_exenta_from_paid_payment_path(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)

        for tipo_dte in ('56', '61'):
            response = self.client.post(
                reverse('sii-dte-generate'),
                {'pago_mensual_id': pago.id, 'tipo_dte': tipo_dte},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(DTEEmitido.objects.filter(pago_mensual=pago).count(), 0)

    def test_update_dte_status_manually(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {
                'estado_dte': 'enviado_manual_controlado',
                'sii_track_id': '0245399452',
                'ultimo_estado_sii': 'Recibido',
            },
            format='json',
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data['estado_dte'], 'enviado_manual_controlado')
        self.assertEqual(update.data['sii_track_id'], '0245399452')
        event = AuditEvent.objects.get(
            event_type='sii.dte_emitido.status_updated',
            entity_type='dte_emitido',
            entity_id=str(generated.data['id']),
        )
        self._assert_transition_metadata(
            event,
            field='estado_dte',
            previous='borrador',
            current='enviado_manual_controlado',
        )
        self.assertEqual(event.metadata['sii_track_id'], '0245399452')

    def test_dte_status_audit_metadata_redacts_inherited_sensitive_tracking_ref(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        DTEEmitido.objects.filter(pk=generated.data['id']).update(
            sii_track_id='https://sii.example.test/track?token=secret'
        )

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {'estado_dte': 'borrador'},
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data['sii_track_id'], REDACTED_SENSITIVE_REFERENCE)
        event = AuditEvent.objects.filter(
            event_type='sii.dte_emitido.status_updated',
            entity_id=str(generated.data['id']),
        ).latest('id')
        self.assertEqual(event.metadata['sii_track_id'], REDACTED_SENSITIVE_REFERENCE)
        serialized_metadata = json.dumps(event.metadata)
        self.assertNotIn('sii.example.test', serialized_metadata)
        self.assertNotIn('token', serialized_metadata)
        self.assertNotIn('secret', serialized_metadata)

    def test_update_dte_status_requires_tracking_reference_for_external_state(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {
                'estado_dte': 'aceptado',
            },
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sii_track_id', update.data['detail'])

    def test_update_final_dte_status_requires_status_query_capability(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {
                'estado_dte': 'aceptado',
                'sii_track_id': 'dte-status-track-001',
                'ultimo_estado_sii': 'Aceptado',
            },
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('DTEConsultaEstado', update.data['detail'])

    def test_update_final_dte_status_accepts_ready_status_query_capability(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        self._activate_capability(
            empresa,
            estado_gate='abierto',
            capacidad_key='DTEConsultaEstado',
            prefix='dte-status',
        )
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {
                'estado_dte': 'aceptado',
                'sii_track_id': 'dte-status-track-002',
                'ultimo_estado_sii': 'Aceptado',
            },
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data['estado_dte'], 'aceptado')
        self.assertEqual(update.data['ultimo_estado_sii'], 'Aceptado')

    def test_update_dte_external_status_rejects_inherited_invalid_artifact(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        f29_capability = self._activate_capability(
            empresa,
            estado_gate='abierto',
            capacidad_key='F29Preparacion',
            prefix='f29',
        )
        self.assertEqual(f29_capability.status_code, status.HTTP_201_CREATED)
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        DTEEmitido.objects.filter(pk=generated.data['id']).update(capacidad_tributaria_id=f29_capability.data['id'])

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {
                'estado_dte': 'enviado_manual_controlado',
                'sii_track_id': 'dte-invalid-capability-track',
            },
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('capacidad_tributaria', update.data['detail'])
        self.assertEqual(DTEEmitido.objects.get(pk=generated.data['id']).estado_dte, 'borrador')
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type='sii.dte_emitido.status_updated',
                entity_id=str(generated.data['id']),
            ).exists()
        )

    def test_sii_status_updates_reject_sensitive_references(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        self._activate_capability(empresa, estado_gate='abierto')
        generated_dte = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated_dte.status_code, status.HTTP_201_CREATED)

        dte_update = self.client.post(
            reverse('sii-dte-status', args=[generated_dte.data['id']]),
            {
                'estado_dte': 'aceptado',
                'sii_track_id': 'https://sii.example.test/track?token=secret',
                'ultimo_estado_sii': 'Aceptado',
            },
            format='json',
        )
        self.assertEqual(dte_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sii_track_id', dte_update.data['detail'])

        dte_observations_update = self.client.post(
            reverse('sii-dte-status', args=[generated_dte.data['id']]),
            {
                'estado_dte': 'borrador',
                'observaciones': 'No registrar https://sii.example.test/dte?token=secret',
            },
            format='json',
        )
        self.assertEqual(dte_observations_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('observaciones', dte_observations_update.data['detail'])

        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        generated_f29 = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated_f29.status_code, status.HTTP_201_CREATED)
        f29_update = self.client.post(
            reverse('sii-f29-status', args=[generated_f29.data['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'borrador_ref': 'https://sii.example.test/f29?token=secret',
            },
            format='json',
        )
        self.assertEqual(f29_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('borrador_ref', f29_update.data['detail'])

        f29_observations_update = self.client.post(
            reverse('sii-f29-status', args=[generated_f29.data['id']]),
            {
                'estado_preparacion': generated_f29.data['estado_preparacion'],
                'observaciones': 'No registrar https://sii.example.test/f29?token=secret',
            },
            format='json',
        )
        self.assertEqual(f29_observations_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('observaciones', f29_observations_update.data['detail'])

        annual_empresa = Empresa.objects.create(
            razon_social='Annual Sensitive SpA',
            rut='33333333-3',
            estado='activa',
        )
        self._activate_fiscal_config(annual_empresa, ddjj_habilitadas=['1887'])
        self._activate_annual_capabilities(annual_empresa)
        self._create_twelve_approved_closes(annual_empresa, fiscal_year=2026)
        generated_annual = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': annual_empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated_annual.status_code, status.HTTP_201_CREATED)
        ddjj_update = self.client.post(
            reverse('sii-ddjj-status', args=[generated_annual.data['ddjj_preparacion']['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'ref_value': 'https://sii.example.test/ddjj?token=secret',
            },
            format='json',
        )
        self.assertEqual(ddjj_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ref_value', ddjj_update.data['detail'])

        ddjj_observations_update = self.client.post(
            reverse('sii-ddjj-status', args=[generated_annual.data['ddjj_preparacion']['id']]),
            {
                'estado_preparacion': generated_annual.data['ddjj_preparacion']['estado_preparacion'],
                'observaciones': 'No registrar https://sii.example.test/ddjj?token=secret',
            },
            format='json',
        )
        self.assertEqual(ddjj_observations_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('observaciones', ddjj_observations_update.data['detail'])

        f22_observations_update = self.client.post(
            reverse('sii-f22-status', args=[generated_annual.data['f22_preparacion']['id']]),
            {
                'estado_preparacion': generated_annual.data['f22_preparacion']['estado_preparacion'],
                'observaciones': 'No registrar https://sii.example.test/f22?token=secret',
            },
            format='json',
        )
        self.assertEqual(f22_observations_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('observaciones', f22_observations_update.data['detail'])

    def test_generate_f29_requires_capability_and_approved_close(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        response = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_f29_rejects_conditioned_gate(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'condicionado',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')

        response = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        response = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_f29_uses_obligations_and_returns_prepared_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')

        response = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado_preparacion'], 'preparado')
        self.assertEqual(len(response.data['resumen_formulario']['obligaciones']), 1)

    def test_generate_f29_returns_pending_data_when_obligation_is_not_ready(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='pendiente_datos')

        response = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado_preparacion'], 'pendiente_datos')

    def test_update_f29_status_rechecks_gate_for_prepared_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='pendiente_datos')
        generated = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        CapacidadTributariaSII.objects.filter(empresa=empresa, capacidad_key='F29Preparacion').update(
            estado_gate='condicionado'
        )

        update = self.client.post(
            reverse('sii-f29-status', args=[generated.data['id']]),
            {'estado_preparacion': 'preparado'},
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('gate', update.data['detail'])

    def test_update_f29_status_rejects_inherited_invalid_artifact(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        dte_capability = self._activate_capability(empresa, estado_gate='abierto')
        self.assertEqual(dte_capability.status_code, status.HTTP_201_CREATED)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        generated = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        F29PreparacionMensual.objects.filter(pk=generated.data['id']).update(
            capacidad_tributaria_id=dte_capability.data['id']
        )

        update = self.client.post(
            reverse('sii-f29-status', args=[generated.data['id']]),
            {'estado_preparacion': 'preparado'},
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('capacidad_tributaria', update.data['detail'])
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type='sii.f29_preparacion.status_updated',
                entity_id=str(generated.data['id']),
            ).exists()
        )

    def test_update_f29_status_manually(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        generated = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-f29-status', args=[generated.data['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'borrador_ref': 'f29-2026-01',
                'responsable_revision_ref': 'tax-reviewer-f29-2026-01',
            },
            format='json',
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data['estado_preparacion'], 'aprobado_para_presentacion')
        self.assertEqual(update.data['responsable_revision_ref'], 'tax-reviewer-f29-2026-01')
        event = AuditEvent.objects.get(
            event_type='sii.f29_preparacion.status_updated',
            entity_type='f29_preparacion',
            entity_id=str(generated.data['id']),
        )
        self._assert_transition_metadata(
            event,
            field='estado_preparacion',
            previous='preparado',
            current='aprobado_para_presentacion',
        )
        self.assertEqual(event.metadata['responsable_revision_ref'], 'tax-reviewer-f29-2026-01')

    def test_update_f29_status_requires_borrador_ref_for_approved_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        generated = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-f29-status', args=[generated.data['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
            },
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('borrador_ref', update.data['detail'])

    def test_update_f29_status_requires_responsable_for_approved_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        generated = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('sii-f29-status', args=[generated.data['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'borrador_ref': 'f29-2026-01',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('responsable_revision_ref', response.data['detail'])

    def test_monthly_sii_workflow_from_paid_payment_to_dte_and_f29(self):
        empresa, pago = self._setup_paid_payment(monto_facturable='100000.00', monto_cobrado='100111.00')
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)

        dte = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(dte.status_code, status.HTTP_201_CREATED)
        self.assertEqual(dte.data['monto_neto_clp'], '100000.00')
        self.assertEqual(dte.data['estado_dte'], 'borrador')

        dte_status = self.client.post(
            reverse('sii-dte-status', args=[dte.data['id']]),
            {
                'estado_dte': 'enviado_manual_controlado',
                'sii_track_id': '0245399452',
                'ultimo_estado_sii': 'Recibido',
            },
            format='json',
        )
        self.assertEqual(dte_status.status_code, status.HTTP_200_OK)
        self.assertEqual(dte_status.data['estado_dte'], 'enviado_manual_controlado')

        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')

        f29 = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(f29.status_code, status.HTTP_201_CREATED)
        self.assertEqual(f29.data['estado_preparacion'], 'preparado')
        self.assertEqual(len(f29.data['resumen_formulario']['obligaciones']), 1)

        f29_status = self.client.post(
            reverse('sii-f29-status', args=[f29.data['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'borrador_ref': 'f29-2026-01',
                'responsable_revision_ref': 'tax-reviewer-f29-2026-01',
            },
            format='json',
        )
        self.assertEqual(f29_status.status_code, status.HTTP_200_OK)
        self.assertEqual(f29_status.data['estado_preparacion'], 'aprobado_para_presentacion')
        self.assertEqual(f29_status.data['responsable_revision_ref'], 'tax-reviewer-f29-2026-01')

    def test_generate_annual_preparation_requires_twelve_approved_closes(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        self._activate_annual_capabilities(empresa)

        response = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_annual_preparation_requires_approved_tax_year_ruleset(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(
            empresa,
            ddjj_habilitadas=['1887'],
            with_tax_year_ruleset=False,
        )
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)

        response = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('TaxYearRuleSet', response.data['detail'])

    def test_generate_annual_preparation_rejects_conditioned_gates(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        for capability_key in ('DDJJPreparacion', 'F22Preparacion'):
            response = self.client.post(
                reverse('sii-capacidad-list'),
                {
                    'empresa': empresa.id,
                    'capacidad_key': capability_key,
                    'certificado_ref': f'cert-{capability_key}',
                    'ambiente': 'certificacion',
                    'estado_gate': 'condicionado',
                    'ultimo_resultado': {},
                },
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)

        response = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_annual_preparation_builds_ddjj_and_f22(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)

        response = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['proceso_renta_anual']['estado'], 'preparado')
        self.assertEqual(response.data['ddjj_preparacion']['estado_preparacion'], 'preparado')
        self.assertEqual(response.data['f22_preparacion']['estado_preparacion'], 'preparado')
        process = ProcesoRentaAnual.objects.get(pk=response.data['proceso_renta_anual']['id'])
        self.assertIsNotNone(process.source_bundle_id)
        self.assertEqual(process.source_bundle.estado, EstadoAnnualTaxSourceBundle.FROZEN)
        self.assertEqual(process.source_bundle.anio_comercial, 2026)
        self.assertEqual(process.source_bundle.resumen_fuentes['approved_close_months'], list(range(1, 13)))
        self.assertEqual(process.source_bundle.resumen_fuentes['obligation_months'], list(range(1, 13)))
        self.assertEqual(process.resumen_anual['annual_tax_source_bundle']['id'], process.source_bundle_id)
        self.assertEqual(
            process.resumen_anual['annual_tax_source_bundle']['hash_fuentes'],
            process.source_bundle.hash_fuentes,
        )
        monthly_facts = MonthlyTaxFact.objects.filter(
            empresa=empresa,
            anio=2026,
            estado=EstadoMonthlyTaxFact.NORMALIZED,
        )
        self.assertEqual(monthly_facts.count(), 12)
        self.assertEqual(process.resumen_anual['annual_tax_monthly_facts']['total'], 12)
        self.assertEqual(process.resumen_anual['annual_tax_monthly_facts']['months'], list(range(1, 13)))
        self.assertEqual(process.resumen_anual['annual_tax_monthly_facts']['obligations_total'], 12)
        self.assertEqual(process.resumen_anual['annual_tax_monthly_facts']['rent_distributions_total'], 1)
        workbooks = AnnualTaxWorkbook.objects.filter(proceso_renta_anual=process).order_by('tipo')
        workbook_lines = AnnualTaxWorkbookLine.objects.filter(workbook__proceso_renta_anual=process)
        self.assertEqual(workbooks.count(), 2)
        self.assertEqual(workbook_lines.count(), 2)
        self.assertEqual(process.resumen_anual['annual_tax_workbooks']['total'], 2)
        self.assertEqual(process.resumen_anual['annual_tax_workbooks']['types'], ['CPT', 'RLI'])
        self.assertEqual(process.resumen_anual['annual_tax_workbooks']['by_type']['RLI']['warnings_total'], 0)
        self.assertEqual(process.resumen_anual['annual_tax_workbooks']['by_type']['CPT']['warnings_total'], 0)
        enterprise_registers = AnnualEnterpriseRegisterSet.objects.filter(proceso_renta_anual=process).order_by('tipo_registro')
        enterprise_movements = AnnualEnterpriseRegisterMovement.objects.filter(register_set__proceso_renta_anual=process)
        self.assertEqual(enterprise_registers.count(), 4)
        self.assertGreaterEqual(enterprise_movements.count(), 6)
        self.assertEqual(process.resumen_anual['annual_enterprise_registers']['total'], 4)
        self.assertEqual(
            process.resumen_anual['annual_enterprise_registers']['types'],
            ['DIVIDENDOS', 'RAI', 'RETIROS', 'SAC'],
        )
        self.assertEqual(process.resumen_anual['annual_enterprise_registers']['by_type']['RAI']['warnings_total'], 0)
        self.assertEqual(process.resumen_anual['annual_enterprise_registers']['by_type']['SAC']['warnings_total'], 0)
        real_estate_sections = AnnualRealEstateSection.objects.filter(proceso_renta_anual=process)
        real_estate_items = AnnualRealEstateItem.objects.filter(section__proceso_renta_anual=process)
        self.assertEqual(real_estate_sections.count(), 1)
        self.assertEqual(real_estate_items.count(), 1)
        self.assertEqual(process.resumen_anual['annual_real_estate_sections']['total'], 1)
        section_summary = next(iter(process.resumen_anual['annual_real_estate_sections']['by_id'].values()))
        self.assertEqual(section_summary['propiedades_total'], 1)
        self.assertEqual(section_summary['items_total'], 1)
        self.assertEqual(section_summary['warnings_total'], 0)
        artifact_matrices = AnnualTaxArtifactMatrix.objects.filter(proceso_renta_anual=process)
        artifact_items = AnnualTaxArtifactMatrixItem.objects.filter(matrix__proceso_renta_anual=process)
        self.assertEqual(artifact_matrices.count(), 1)
        self.assertGreaterEqual(artifact_items.count(), 10)
        self.assertEqual(process.resumen_anual['annual_tax_artifact_matrices']['total'], 1)
        matrix_summary = next(iter(process.resumen_anual['annual_tax_artifact_matrices']['by_id'].values()))
        self.assertEqual(matrix_summary['items_total'], artifact_items.count())
        self.assertGreater(matrix_summary['ddjj_items_total'], 0)
        self.assertGreater(matrix_summary['f22_items_total'], 0)
        self.assertEqual(matrix_summary['warnings_total'], 0)

        monthly_facts_response = self.client.get(reverse('sii-monthly-tax-fact-list'))
        self.assertEqual(monthly_facts_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(monthly_facts_response.data), 12)
        workbook_response = self.client.get(reverse('sii-annual-tax-workbook-list'))
        workbook_line_response = self.client.get(reverse('sii-annual-tax-workbook-line-list'))
        enterprise_register_response = self.client.get(reverse('sii-annual-enterprise-register-list'))
        enterprise_movement_response = self.client.get(reverse('sii-annual-enterprise-register-movement-list'))
        real_estate_section_response = self.client.get(reverse('sii-annual-real-estate-section-list'))
        real_estate_item_response = self.client.get(reverse('sii-annual-real-estate-item-list'))
        artifact_matrix_response = self.client.get(reverse('sii-annual-tax-artifact-matrix-list'))
        artifact_matrix_item_response = self.client.get(reverse('sii-annual-tax-artifact-matrix-item-list'))
        self.assertEqual(workbook_response.status_code, status.HTTP_200_OK)
        self.assertEqual(workbook_line_response.status_code, status.HTTP_200_OK)
        self.assertEqual(enterprise_register_response.status_code, status.HTTP_200_OK)
        self.assertEqual(enterprise_movement_response.status_code, status.HTTP_200_OK)
        self.assertEqual(real_estate_section_response.status_code, status.HTTP_200_OK)
        self.assertEqual(real_estate_item_response.status_code, status.HTTP_200_OK)
        self.assertEqual(artifact_matrix_response.status_code, status.HTTP_200_OK)
        self.assertEqual(artifact_matrix_item_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(workbook_response.data), 2)
        self.assertEqual(len(workbook_line_response.data), 2)
        self.assertEqual(len(enterprise_register_response.data), 4)
        self.assertGreaterEqual(len(enterprise_movement_response.data), 6)
        self.assertEqual(len(real_estate_section_response.data), 1)
        self.assertEqual(len(real_estate_item_response.data), 1)
        self.assertEqual(len(artifact_matrix_response.data), 1)
        self.assertEqual(len(artifact_matrix_item_response.data), artifact_items.count())
        snapshot = self.client.get(reverse('sii-snapshot'))
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        self.assertEqual(len(snapshot.data['monthly_tax_facts']), 12)
        self.assertEqual(len(snapshot.data['annual_tax_workbooks']), 2)
        self.assertEqual(len(snapshot.data['annual_tax_workbook_lines']), 2)
        self.assertEqual(len(snapshot.data['annual_enterprise_registers']), 4)
        self.assertGreaterEqual(len(snapshot.data['annual_enterprise_register_movements']), 6)
        self.assertEqual(len(snapshot.data['annual_real_estate_sections']), 1)
        self.assertEqual(len(snapshot.data['annual_real_estate_items']), 1)
        self.assertEqual(len(snapshot.data['annual_tax_artifact_matrices']), 1)
        self.assertEqual(len(snapshot.data['annual_tax_artifact_matrix_items']), artifact_items.count())

    def test_real_estate_item_preserves_frozen_snapshot_after_property_master_changes(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        item = AnnualRealEstateItem.objects.select_related('propiedad').get()
        original_snapshot = {
            'direccion_snapshot': item.direccion_snapshot,
            'comuna_snapshot': item.comuna_snapshot,
            'region_snapshot': item.region_snapshot,
            'hash_item': item.hash_item,
        }

        Propiedad.objects.filter(pk=item.propiedad_id).update(
            direccion='Direccion maestra actualizada 123',
            comuna='Comuna Actualizada',
            region='Region Actualizada',
        )
        item.refresh_from_db()
        item.full_clean()

        self.assertEqual(item.direccion_snapshot, original_snapshot['direccion_snapshot'])
        self.assertEqual(item.comuna_snapshot, original_snapshot['comuna_snapshot'])
        self.assertEqual(item.region_snapshot, original_snapshot['region_snapshot'])
        self.assertEqual(item.hash_item, original_snapshot['hash_item'])

    def test_monthly_tax_fact_admin_and_api_redact_sensitive_payloads(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        fact = MonthlyTaxFact.objects.get(empresa=empresa, anio=2026, mes=1)
        MonthlyTaxFact.objects.filter(pk=fact.pk).update(
            source_ref='https://sii.example.test/monthly?token=secret',
            responsible_ref='Bearer monthly-secret',
            resumen_hecho={'api_key': 'secret-monthly-value'},
        )
        fact.refresh_from_db()
        fact_admin = MonthlyTaxFactAdmin(MonthlyTaxFact, AdminSite())

        self.assertEqual(fact_admin.source_ref_redacted(fact), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(fact_admin.responsible_ref_redacted(fact), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret-monthly-value', json.dumps(fact_admin.resumen_hecho_redacted(fact)))

        monthly_facts_response = self.client.get(reverse('sii-monthly-tax-fact-list'))
        snapshot = self.client.get(reverse('sii-snapshot'))
        serialized_payload = json.dumps(
            {
                'monthly_facts': monthly_facts_response.data,
                'snapshot': snapshot.data,
            },
            default=str,
        )
        self.assertEqual(monthly_facts_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        monthly_fact_data = next(item for item in monthly_facts_response.data if item['id'] == fact.id)
        snapshot_fact_data = next(item for item in snapshot.data['monthly_tax_facts'] if item['id'] == fact.id)
        self.assertEqual(monthly_fact_data['source_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(monthly_fact_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_fact_data['source_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_fact_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('token=secret', serialized_payload)
        self.assertNotIn('monthly-secret', serialized_payload)
        self.assertNotIn('secret-monthly-value', serialized_payload)

    def test_annual_tax_workbook_admin_and_api_redact_sensitive_payloads(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        workbook = AnnualTaxWorkbook.objects.get(empresa=empresa, anio_tributario=2027, tipo='RLI')
        line = workbook.lines.get(codigo_destino='RLI-CONTROL')
        AnnualTaxWorkbook.objects.filter(pk=workbook.pk).update(
            source_ref='https://sii.example.test/rli?token=secret',
            responsible_ref='Bearer workbook-secret',
            resumen_workbook={'api_key': 'secret-workbook-value'},
        )
        AnnualTaxWorkbookLine.objects.filter(pk=line.pk).update(
            formula_ref='https://sii.example.test/formula?token=secret',
            evidencia_ref='Bearer line-secret',
            warnings=['https://sii.example.test/warning?token=secret'],
            source_payload={'api_key': 'secret-line-value'},
        )
        workbook.refresh_from_db()
        line.refresh_from_db()
        workbook_admin = AnnualTaxWorkbookAdmin(AnnualTaxWorkbook, AdminSite())
        line_admin = AnnualTaxWorkbookLineAdmin(AnnualTaxWorkbookLine, AdminSite())

        self.assertEqual(workbook_admin.source_ref_redacted(workbook), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(workbook_admin.responsible_ref_redacted(workbook), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret-workbook-value', json.dumps(workbook_admin.resumen_workbook_redacted(workbook)))
        self.assertEqual(line_admin.formula_ref_redacted(line), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(line_admin.evidencia_ref_redacted(line), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret-line-value', json.dumps(line_admin.source_payload_redacted(line)))

        workbook_response = self.client.get(reverse('sii-annual-tax-workbook-list'))
        line_response = self.client.get(reverse('sii-annual-tax-workbook-line-list'))
        snapshot = self.client.get(reverse('sii-snapshot'))
        serialized_payload = json.dumps(
            {
                'workbooks': workbook_response.data,
                'lines': line_response.data,
                'snapshot': snapshot.data,
            },
            default=str,
        )
        self.assertEqual(workbook_response.status_code, status.HTTP_200_OK)
        self.assertEqual(line_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        workbook_data = next(item for item in workbook_response.data if item['id'] == workbook.id)
        line_data = next(item for item in line_response.data if item['id'] == line.id)
        snapshot_workbook_data = next(item for item in snapshot.data['annual_tax_workbooks'] if item['id'] == workbook.id)
        snapshot_line_data = next(item for item in snapshot.data['annual_tax_workbook_lines'] if item['id'] == line.id)
        self.assertEqual(workbook_data['source_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(workbook_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_workbook_data['source_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_workbook_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(line_data['formula_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(line_data['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_line_data['formula_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_line_data['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('token=secret', serialized_payload)
        self.assertNotIn('workbook-secret', serialized_payload)
        self.assertNotIn('line-secret', serialized_payload)
        self.assertNotIn('secret-workbook-value', serialized_payload)
        self.assertNotIn('secret-line-value', serialized_payload)

    def test_enterprise_register_admin_and_api_redact_sensitive_payloads(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        register = AnnualEnterpriseRegisterSet.objects.get(
            empresa=empresa,
            anio_tributario=2027,
            tipo_registro='RAI',
        )
        movement = AnnualEnterpriseRegisterMovement.objects.filter(
            register_set__empresa=empresa,
            register_set__anio_tributario=2027,
        ).first()
        self.assertIsNotNone(movement)
        AnnualEnterpriseRegisterSet.objects.filter(pk=register.pk).update(
            source_ref='https://sii.example.test/rai?token=secret',
            responsible_ref='Bearer register-secret',
            resumen_registro={'api_key': 'secret-register-value'},
        )
        AnnualEnterpriseRegisterMovement.objects.filter(pk=movement.pk).update(
            formula_ref='https://sii.example.test/register-formula?token=secret',
            evidencia_ref='Bearer movement-secret',
            warnings=['https://sii.example.test/register-warning?token=secret'],
            source_payload={'api_key': 'secret-movement-value'},
        )
        register.refresh_from_db()
        movement.refresh_from_db()
        register_admin = AnnualEnterpriseRegisterSetAdmin(AnnualEnterpriseRegisterSet, AdminSite())
        movement_admin = AnnualEnterpriseRegisterMovementAdmin(AnnualEnterpriseRegisterMovement, AdminSite())

        self.assertEqual(register_admin.source_ref_redacted(register), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(register_admin.responsible_ref_redacted(register), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret-register-value', json.dumps(register_admin.resumen_registro_redacted(register)))
        self.assertEqual(movement_admin.formula_ref_redacted(movement), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(movement_admin.evidencia_ref_redacted(movement), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret-movement-value', json.dumps(movement_admin.source_payload_redacted(movement)))

        register_response = self.client.get(reverse('sii-annual-enterprise-register-list'))
        movement_response = self.client.get(reverse('sii-annual-enterprise-register-movement-list'))
        snapshot = self.client.get(reverse('sii-snapshot'))
        serialized_payload = json.dumps(
            {
                'registers': register_response.data,
                'movements': movement_response.data,
                'snapshot': snapshot.data,
            },
            default=str,
        )
        self.assertEqual(register_response.status_code, status.HTTP_200_OK)
        self.assertEqual(movement_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        register_data = next(item for item in register_response.data if item['id'] == register.id)
        movement_data = next(item for item in movement_response.data if item['id'] == movement.id)
        snapshot_register_data = next(
            item for item in snapshot.data['annual_enterprise_registers'] if item['id'] == register.id
        )
        snapshot_movement_data = next(
            item for item in snapshot.data['annual_enterprise_register_movements'] if item['id'] == movement.id
        )
        self.assertEqual(register_data['source_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(register_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_register_data['source_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_register_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(movement_data['formula_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(movement_data['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_movement_data['formula_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_movement_data['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('token=secret', serialized_payload)
        self.assertNotIn('register-secret', serialized_payload)
        self.assertNotIn('movement-secret', serialized_payload)
        self.assertNotIn('secret-register-value', serialized_payload)
        self.assertNotIn('secret-movement-value', serialized_payload)

    def test_real_estate_section_admin_and_api_redact_sensitive_payloads(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        section = AnnualRealEstateSection.objects.get(empresa=empresa, anio_tributario=2027)
        item = AnnualRealEstateItem.objects.get(section=section)
        AnnualRealEstateSection.objects.filter(pk=section.pk).update(
            source_ref='https://sii.example.test/real-estate?token=secret',
            responsible_ref='Bearer real-estate-secret',
            resumen_seccion={'api_key': 'secret-real-estate-value'},
        )
        AnnualRealEstateItem.objects.filter(pk=item.pk).update(
            formula_ref='https://sii.example.test/real-estate-formula?token=secret',
            evidencia_ref='Bearer real-estate-item-secret',
            warnings=['https://sii.example.test/real-estate-warning?token=secret'],
            source_payload={'api_key': 'secret-real-estate-item-value'},
        )
        section.refresh_from_db()
        item.refresh_from_db()
        section_admin = AnnualRealEstateSectionAdmin(AnnualRealEstateSection, AdminSite())
        item_admin = AnnualRealEstateItemAdmin(AnnualRealEstateItem, AdminSite())

        self.assertEqual(section_admin.source_ref_redacted(section), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(section_admin.responsible_ref_redacted(section), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret-real-estate-value', json.dumps(section_admin.resumen_seccion_redacted(section)))
        self.assertEqual(item_admin.formula_ref_redacted(item), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(item_admin.evidencia_ref_redacted(item), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret-real-estate-item-value', json.dumps(item_admin.source_payload_redacted(item)))

        section_response = self.client.get(reverse('sii-annual-real-estate-section-list'))
        item_response = self.client.get(reverse('sii-annual-real-estate-item-list'))
        snapshot = self.client.get(reverse('sii-snapshot'))
        serialized_payload = json.dumps(
            {
                'sections': section_response.data,
                'items': item_response.data,
                'snapshot': snapshot.data,
            },
            default=str,
        )
        self.assertEqual(section_response.status_code, status.HTTP_200_OK)
        self.assertEqual(item_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        section_data = next(entry for entry in section_response.data if entry['id'] == section.id)
        item_data = next(entry for entry in item_response.data if entry['id'] == item.id)
        snapshot_section_data = next(
            entry for entry in snapshot.data['annual_real_estate_sections'] if entry['id'] == section.id
        )
        snapshot_item_data = next(
            entry for entry in snapshot.data['annual_real_estate_items'] if entry['id'] == item.id
        )
        self.assertEqual(section_data['source_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(section_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_section_data['source_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_section_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(item_data['formula_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(item_data['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_item_data['formula_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_item_data['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('token=secret', serialized_payload)
        self.assertNotIn('real-estate-secret', serialized_payload)
        self.assertNotIn('real-estate-item-secret', serialized_payload)
        self.assertNotIn('secret-real-estate-value', serialized_payload)
        self.assertNotIn('secret-real-estate-item-value', serialized_payload)

    def test_artifact_matrix_admin_and_api_redact_sensitive_payloads(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        matrix = AnnualTaxArtifactMatrix.objects.get(empresa=empresa, anio_tributario=2027)
        item = AnnualTaxArtifactMatrixItem.objects.filter(matrix=matrix).first()
        self.assertIsNotNone(item)
        AnnualTaxArtifactMatrix.objects.filter(pk=matrix.pk).update(
            source_ref='https://sii.example.test/artifact-matrix?token=secret',
            responsible_ref='Bearer artifact-matrix-secret',
            resumen_matriz={'api_key': 'secret-artifact-matrix-value'},
        )
        AnnualTaxArtifactMatrixItem.objects.filter(pk=item.pk).update(
            formula_ref='https://sii.example.test/artifact-formula?token=secret',
            evidencia_ref='Bearer artifact-item-secret',
            responsible_ref='https://sii.example.test/artifact-responsible?token=secret',
            warnings=['https://sii.example.test/artifact-warning?token=secret'],
            source_payload={'api_key': 'secret-artifact-item-value'},
        )
        matrix.refresh_from_db()
        item.refresh_from_db()
        matrix_admin = AnnualTaxArtifactMatrixAdmin(AnnualTaxArtifactMatrix, AdminSite())
        item_admin = AnnualTaxArtifactMatrixItemAdmin(AnnualTaxArtifactMatrixItem, AdminSite())

        self.assertEqual(matrix_admin.source_ref_redacted(matrix), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(matrix_admin.responsible_ref_redacted(matrix), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret-artifact-matrix-value', json.dumps(matrix_admin.resumen_matriz_redacted(matrix)))
        self.assertEqual(item_admin.formula_ref_redacted(item), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(item_admin.evidencia_ref_redacted(item), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(item_admin.responsible_ref_redacted(item), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('secret-artifact-item-value', json.dumps(item_admin.source_payload_redacted(item)))

        matrix_response = self.client.get(reverse('sii-annual-tax-artifact-matrix-list'))
        item_response = self.client.get(reverse('sii-annual-tax-artifact-matrix-item-list'))
        snapshot = self.client.get(reverse('sii-snapshot'))
        serialized_payload = json.dumps(
            {
                'matrices': matrix_response.data,
                'items': item_response.data,
                'snapshot': snapshot.data,
            },
            default=str,
        )
        self.assertEqual(matrix_response.status_code, status.HTTP_200_OK)
        self.assertEqual(item_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        matrix_data = next(entry for entry in matrix_response.data if entry['id'] == matrix.id)
        item_data = next(entry for entry in item_response.data if entry['id'] == item.id)
        snapshot_matrix_data = next(
            entry for entry in snapshot.data['annual_tax_artifact_matrices'] if entry['id'] == matrix.id
        )
        snapshot_item_data = next(
            entry for entry in snapshot.data['annual_tax_artifact_matrix_items'] if entry['id'] == item.id
        )
        self.assertEqual(matrix_data['source_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(matrix_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_matrix_data['source_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_matrix_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(item_data['formula_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(item_data['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(item_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_item_data['formula_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_item_data['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_item_data['responsible_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('token=secret', serialized_payload)
        self.assertNotIn('artifact-matrix-secret', serialized_payload)
        self.assertNotIn('artifact-item-secret', serialized_payload)
        self.assertNotIn('secret-artifact-matrix-value', serialized_payload)
        self.assertNotIn('secret-artifact-item-value', serialized_payload)

    def test_generate_annual_preparation_rejects_source_changes_after_bundle_freeze(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        ObligacionTributariaMensual.objects.filter(
            empresa=empresa,
            anio=2026,
            mes=12,
            obligacion_tipo='PPM',
        ).update(monto_calculado='20022.20')
        response = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('AnnualTaxSourceBundle congelado existente', response.data['detail'])

    def test_annual_sii_workflow_prepares_and_updates_ddjj_and_f22(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)

        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        self.assertEqual(generated.data['proceso_renta_anual']['estado'], 'preparado')
        self.assertEqual(generated.data['ddjj_preparacion']['estado_preparacion'], 'preparado')
        self.assertEqual(generated.data['f22_preparacion']['estado_preparacion'], 'preparado')

        ddjj_status = self.client.post(
            reverse('sii-ddjj-status', args=[generated.data['ddjj_preparacion']['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'ref_value': 'ddjj-2027',
                'responsable_revision_ref': 'tax-reviewer-ddjj-2027',
                'observaciones': 'Paquete DDJJ listo.',
            },
            format='json',
        )
        self.assertEqual(ddjj_status.status_code, status.HTTP_200_OK)
        self.assertEqual(ddjj_status.data['estado_preparacion'], 'aprobado_para_presentacion')
        self.assertEqual(ddjj_status.data['paquete_ref'], 'ddjj-2027')
        self.assertEqual(ddjj_status.data['responsable_revision_ref'], 'tax-reviewer-ddjj-2027')
        ddjj_event = AuditEvent.objects.get(
            event_type='sii.ddjj_preparacion.status_updated',
            entity_type='ddjj_preparacion',
            entity_id=str(generated.data['ddjj_preparacion']['id']),
        )
        self._assert_transition_metadata(
            ddjj_event,
            field='estado_preparacion',
            previous='preparado',
            current='aprobado_para_presentacion',
        )
        self.assertEqual(ddjj_event.metadata['responsable_revision_ref'], 'tax-reviewer-ddjj-2027')

        f22_status = self.client.post(
            reverse('sii-f22-status', args=[generated.data['f22_preparacion']['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'ref_value': 'f22-2027',
                'responsable_revision_ref': 'tax-reviewer-f22-2027',
                'observaciones': 'Borrador F22 listo.',
            },
            format='json',
        )
        self.assertEqual(f22_status.status_code, status.HTTP_200_OK)
        self.assertEqual(f22_status.data['estado_preparacion'], 'aprobado_para_presentacion')
        self.assertEqual(f22_status.data['borrador_ref'], 'f22-2027')
        self.assertEqual(f22_status.data['responsable_revision_ref'], 'tax-reviewer-f22-2027')
        f22_event = AuditEvent.objects.get(
            event_type='sii.f22_preparacion.status_updated',
            entity_type='f22_preparacion',
            entity_id=str(generated.data['f22_preparacion']['id']),
        )
        self._assert_transition_metadata(
            f22_event,
            field='estado_preparacion',
            previous='preparado',
            current='aprobado_para_presentacion',
        )
        self.assertEqual(f22_event.metadata['responsable_revision_ref'], 'tax-reviewer-f22-2027')

        process = ProcesoRentaAnual.objects.get(pk=generated.data['proceso_renta_anual']['id'])
        ddjj = DDJJPreparacionAnual.objects.get(pk=generated.data['ddjj_preparacion']['id'])
        f22 = F22PreparacionAnual.objects.get(pk=generated.data['f22_preparacion']['id'])

        self.assertEqual(process.paquete_ddjj_ref, 'ddjj-2027')
        self.assertEqual(process.borrador_f22_ref, 'f22-2027')
        self.assertEqual(process.responsable_revision_ref, 'tax-reviewer-f22-2027')
        self.assertEqual(ddjj.estado_preparacion, 'aprobado_para_presentacion')
        self.assertEqual(ddjj.responsable_revision_ref, 'tax-reviewer-ddjj-2027')
        self.assertEqual(f22.estado_preparacion, 'aprobado_para_presentacion')
        self.assertEqual(f22.responsable_revision_ref, 'tax-reviewer-f22-2027')

    def test_annual_status_requires_review_responsible_for_approved_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('sii-ddjj-status', args=[generated.data['ddjj_preparacion']['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'ref_value': 'ddjj-2027',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('responsable_revision_ref', response.data['detail'])

    def test_annual_status_rechecks_gate_for_prepared_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        CapacidadTributariaSII.objects.filter(empresa=empresa, capacidad_key='DDJJPreparacion').update(
            estado_gate='condicionado'
        )
        ddjj_status = self.client.post(
            reverse('sii-ddjj-status', args=[generated.data['ddjj_preparacion']['id']]),
            {'estado_preparacion': 'preparado'},
            format='json',
        )
        self.assertEqual(ddjj_status.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('gate', ddjj_status.data['detail'])

        CapacidadTributariaSII.objects.filter(empresa=empresa, capacidad_key='DDJJPreparacion').update(
            estado_gate='abierto'
        )
        CapacidadTributariaSII.objects.filter(empresa=empresa, capacidad_key='F22Preparacion').update(
            estado_gate='condicionado'
        )
        f22_status = self.client.post(
            reverse('sii-f22-status', args=[generated.data['f22_preparacion']['id']]),
            {'estado_preparacion': 'preparado'},
            format='json',
        )
        self.assertEqual(f22_status.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('gate', f22_status.data['detail'])

    def test_annual_status_rejects_inherited_invalid_artifacts(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        ddjj_capability = CapacidadTributariaSII.objects.get(empresa=empresa, capacidad_key='DDJJPreparacion')
        f22_capability = CapacidadTributariaSII.objects.get(empresa=empresa, capacidad_key='F22Preparacion')
        DDJJPreparacionAnual.objects.filter(pk=generated.data['ddjj_preparacion']['id']).update(
            capacidad_tributaria_id=f22_capability.id
        )
        F22PreparacionAnual.objects.filter(pk=generated.data['f22_preparacion']['id']).update(
            capacidad_tributaria_id=ddjj_capability.id
        )

        ddjj_status = self.client.post(
            reverse('sii-ddjj-status', args=[generated.data['ddjj_preparacion']['id']]),
            {'estado_preparacion': 'preparado'},
            format='json',
        )
        f22_status = self.client.post(
            reverse('sii-f22-status', args=[generated.data['f22_preparacion']['id']]),
            {'estado_preparacion': 'preparado'},
            format='json',
        )

        self.assertEqual(ddjj_status.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(f22_status.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('capacidad_tributaria', ddjj_status.data['detail'])
        self.assertIn('capacidad_tributaria', f22_status.data['detail'])
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type__in=('sii.ddjj_preparacion.status_updated', 'sii.f22_preparacion.status_updated'),
            ).exists()
        )

    def test_annual_status_rejects_final_presentation_boundary(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('sii-ddjj-status', args=[generated.data['ddjj_preparacion']['id']]),
            {
                'estado_preparacion': 'presentado',
                'ref_value': 'ddjj-final',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('PresentacionAnualFinal', response.data['detail'])

    def test_generate_annual_preparation_leaves_ddjj_pending_when_no_ddjj_enabled(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=[])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)

        response = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['ddjj_preparacion']['estado_preparacion'], 'pendiente_datos')
        self.assertEqual(response.data['f22_preparacion']['estado_preparacion'], 'preparado')


class SiiMigrationSafetyTests(TransactionTestCase):
    reset_sequences = True

    migrate_from = [
        ('patrimonio', '0002_participaciones_mixtas_y_representacion_comunidad'),
        ('operacion', '0001_initial'),
        ('contratos', '0001_initial'),
        ('cobranza', '0003_pagomensual_monto_facturable_clp'),
        ('sii', '0003_procesorentaanual_f22preparacionanual_and_more'),
    ]
    migrate_to = [
        ('patrimonio', '0003_repair_legacy_representacion_modes'),
        ('operacion', '0001_initial'),
        ('contratos', '0001_initial'),
        ('cobranza', '0004_distribucioncobromensual'),
        ('sii', '0004_dte_emitido_distribucion_cobro_mensual'),
    ]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        self.old_apps = self.executor.loader.project_state(self.migrate_from).apps

    def migrate(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def test_dte_backfill_links_distribution_even_when_legacy_payment_lacked_facturable_amount(self):
        Socio = self.old_apps.get_model('patrimonio', 'Socio')
        Empresa = self.old_apps.get_model('patrimonio', 'Empresa')
        ParticipacionPatrimonial = self.old_apps.get_model('patrimonio', 'ParticipacionPatrimonial')
        Propiedad = self.old_apps.get_model('patrimonio', 'Propiedad')
        CuentaRecaudadora = self.old_apps.get_model('operacion', 'CuentaRecaudadora')
        MandatoOperacion = self.old_apps.get_model('operacion', 'MandatoOperacion')
        Arrendatario = self.old_apps.get_model('contratos', 'Arrendatario')
        Contrato = self.old_apps.get_model('contratos', 'Contrato')
        ContratoPropiedad = self.old_apps.get_model('contratos', 'ContratoPropiedad')
        PeriodoContractual = self.old_apps.get_model('contratos', 'PeriodoContractual')
        PagoMensual = self.old_apps.get_model('cobranza', 'PagoMensual')
        CapacidadTributariaSII = self.old_apps.get_model('sii', 'CapacidadTributariaSII')
        DTEEmitidoOld = self.old_apps.get_model('sii', 'DTEEmitido')

        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        empresa = Empresa.objects.create(razon_social='Empresa Legacy SII', rut='76999999-9', estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio_id=socio_1.id,
            empresa_owner_id=empresa.id,
            porcentaje='60.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio_id=socio_2.id,
            empresa_owner_id=empresa.id,
            porcentaje='40.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        propiedad = Propiedad.objects.create(
            direccion='Av Legacy SII',
            comuna='Santiago',
            region='RM',
            tipo_inmueble='local',
            codigo_propiedad='SII-HIST-001',
            estado='activa',
            empresa_owner_id=empresa.id,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner_id=empresa.id,
            institucion='Banco Uno',
            numero_cuenta='ACC-SII-HIST',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo='activa',
        )
        mandato = MandatoOperacion.objects.create(
            propiedad_id=propiedad.id,
            propietario_empresa_owner_id=empresa.id,
            administrador_empresa_owner_id=empresa.id,
            cuenta_recaudadora_id=cuenta.id,
            entidad_facturadora_id=empresa.id,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado='activa',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario Legacy',
            rut='56565656-5',
            email='legacy@example.com',
            telefono='777',
            domicilio_notificaciones='Legacy',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato='SII-HIST',
            mandato_operacion_id=mandato.id,
            arrendatario_id=arrendatario.id,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            dia_pago_mensual=5,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato_id=contrato.id,
            propiedad_id=propiedad.id,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        periodo = PeriodoContractual.objects.create(
            contrato_id=contrato.id,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='base',
            origen_periodo='manual',
        )
        pago = PagoMensual.objects.create(
            contrato_id=contrato.id,
            periodo_contractual_id=periodo.id,
            mes=1,
            anio=2026,
            monto_facturable_clp='0.00',
            monto_calculado_clp='100111.00',
            monto_pagado_clp='100111.00',
            fecha_vencimiento='2026-01-05',
            estado_pago='pagado',
            codigo_conciliacion_efectivo='111',
        )
        capacidad = CapacidadTributariaSII.objects.create(
            empresa_id=empresa.id,
            capacidad_key='DTEEmision',
            certificado_ref='cert-legacy',
            ambiente='certificacion',
            estado_gate='abierto',
        )
        DTEEmitidoOld.objects.create(
            empresa_id=empresa.id,
            capacidad_tributaria_id=capacidad.id,
            contrato_id=contrato.id,
            pago_mensual_id=pago.id,
            arrendatario_id=arrendatario.id,
            tipo_dte='34',
            monto_neto_clp='100000.00',
            fecha_emision='2026-01-06',
            estado_dte='borrador',
        )

        self.migrate()

        DTEEmitidoNew = self.apps.get_model('sii', 'DTEEmitido')
        dte = DTEEmitidoNew.objects.get(contrato__codigo_contrato='SII-HIST')

        self.assertIsNotNone(dte.distribucion_cobro_mensual_id)
        self.assertTrue(dte.distribucion_cobro_mensual.requiere_dte)
        self.assertEqual(dte.distribucion_cobro_mensual.beneficiario_empresa_owner_id, dte.empresa_id)
