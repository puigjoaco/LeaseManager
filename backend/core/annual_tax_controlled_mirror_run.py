from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from contabilidad.models import (
    BalanceComprobacion,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EstadoCierreMensual,
    LibroDiario,
    NaturalezaCuenta,
)
from core.reference_validation import is_non_sensitive_reference
from sii.models import (
    AnnualTaxDDJJFormLayout,
    AnnualTaxF22ExportLayout,
    AnnualTaxOfficialSource,
    CapacidadSII,
    CapacidadTributariaSII,
    DestinoMapeoTributarioAnual,
    EstadoAnnualTaxDDJJLayout,
    EstadoAnnualTaxF22ExportLayout,
    EstadoAnnualTaxOfficialSource,
    EstadoGateSII,
    EstadoMonthlyTaxFact,
    EstadoReglaTributariaAnual,
    MedioAnnualTaxDDJJ,
    MedioAnnualTaxF22Export,
    MonthlyTaxFact,
    SourceKindRentaAnual,
    TaxCodeMapping,
    TaxYearRuleSet,
    TipoAnnualTaxOfficialSource,
)
from sii.services import freeze_annual_tax_source_bundle, generate_annual_preparation


CONTROLLED_MIRROR_RUN_SCHEMA_VERSION = 'annual-tax-controlled-mirror-run.v1'
DEFAULT_DDJJ_CODES = ('1887',)
REQUIRED_REFERENCES = (
    'source_label',
    'authorization_ref',
    'responsible_ref',
    'fiscal_rule_ref',
    'certificates_proof_ref',
)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _require_reference(value: str, field_name: str) -> str:
    normalized = str(value or '').strip()
    if not normalized:
        raise ValueError(f'{field_name} es obligatorio.')
    if not is_non_sensitive_reference(normalized):
        raise ValueError(f'{field_name} debe ser una referencia no sensible.')
    return normalized


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value is not None else '0.00'))
    except Exception:
        return Decimal('0.00')


def _save_validated(instance) -> None:
    try:
        instance.full_clean()
    except ValidationError as error:
        raise ValueError(error.message_dict if hasattr(error, 'message_dict') else error.messages) from error
    instance.save()


def _active_fiscal_config(empresa) -> ConfiguracionFiscalEmpresa:
    config = ConfiguracionFiscalEmpresa.objects.filter(empresa=empresa, estado='activa').first()
    if config is None:
        raise ValueError('La empresa no tiene ConfiguracionFiscalEmpresa activa.')
    return config


def _normalized_monthly_facts(empresa, commercial_year: int) -> list[MonthlyTaxFact]:
    return list(
        MonthlyTaxFact.objects.filter(
            empresa=empresa,
            anio=commercial_year,
            estado=EstadoMonthlyTaxFact.NORMALIZED,
        ).order_by('mes')
    )


def _monthly_fact_months(empresa, commercial_year: int) -> list[int]:
    return sorted({fact.mes for fact in _normalized_monthly_facts(empresa, commercial_year)})


def _ensure_capability(empresa, capability_key: str, *, ref_prefix: str, fiscal_rule_ref: str) -> CapacidadTributariaSII:
    capability, _ = CapacidadTributariaSII.objects.get_or_create(
        empresa=empresa,
        capacidad_key=capability_key,
    )
    slug = str(capability_key).lower().replace('_', '-')
    capability.certificado_ref = f'{ref_prefix}-{slug}-cert'
    capability.evidencia_ref = f'{ref_prefix}-{slug}-evidence'
    capability.prueba_flujo_ref = f'{ref_prefix}-{slug}-flow'
    capability.autorizacion_ambiente_ref = f'{ref_prefix}-{slug}-certification-env'
    capability.regla_fiscal_ref = fiscal_rule_ref
    capability.estado_gate = EstadoGateSII.OPEN
    capability.ultimo_resultado = {
        'source': 'annual_tax_controlled_mirror_run',
        'uses_real_sii': False,
        'uses_external_auth': False,
        'final_tax_calculation': False,
    }
    _save_validated(capability)
    return capability


def _ensure_official_source(
    *,
    config: ConfiguracionFiscalEmpresa,
    tax_year: int,
    key: str,
    applies_to: str = '',
    source_type: str = TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
    metadata_extra: dict[str, Any] | None = None,
) -> AnnualTaxOfficialSource:
    regime_code = config.regimen_tributario.codigo_regimen
    source_key = f'controlled-mirror-{key}-at{tax_year}-{regime_code}'
    metadata = {
        'source': 'annual_tax_controlled_mirror_run',
        'official': False,
        'uses_real_sii': False,
        'uses_external_auth': False,
        'final_tax_calculation': False,
    }
    metadata.update(metadata_extra or {})
    defaults = {
        'source_type': source_type,
        'title': f'Fuente controlada {key} AT{tax_year}',
        'source_ref': f'controlled-mirror-source-{key}-at{tax_year}',
        'source_hash': _hash_text(source_key),
        'retrieved_on': timezone.localdate(),
        'responsible_ref': f'controlled-mirror-source-reviewer-at{tax_year}',
        'estado': EstadoAnnualTaxOfficialSource.APPROVED,
        'applies_to': applies_to,
        'regime_code': regime_code,
        'scope_note': 'Fuente local controlada para prueba espejo AC/AT; no acredita formato oficial ni presentacion SII.',
        'metadata': metadata,
    }
    source, created = AnnualTaxOfficialSource.objects.get_or_create(
        anio_tributario=tax_year,
        source_key=source_key,
        defaults=defaults,
    )
    if not created:
        for field_name, value in defaults.items():
            setattr(source, field_name, value)
    _save_validated(source)
    return source


def _ensure_tax_year_ruleset(
    *,
    config: ConfiguracionFiscalEmpresa,
    tax_year: int,
    ddjj_codes: tuple[str, ...],
    fiscal_rule_ref: str,
) -> TaxYearRuleSet:
    rule_source = _ensure_official_source(config=config, tax_year=tax_year, key='ruleset')
    rule_set = TaxYearRuleSet.objects.filter(
        anio_tributario=tax_year,
        regimen_tributario=config.regimen_tributario,
        estado=EstadoReglaTributariaAnual.APPROVED,
    ).first()
    if rule_set is None:
        rule_set = TaxYearRuleSet(
            anio_tributario=tax_year,
            regimen_tributario=config.regimen_tributario,
            version=f'AT{tax_year}-controlled-mirror-v1',
        )
    rule_set.estado = EstadoReglaTributariaAnual.APPROVED
    rule_set.fuente_ref = fiscal_rule_ref
    rule_set.hash_normativo = _hash_text(f'{fiscal_rule_ref}-{tax_year}-{config.regimen_tributario_id}')
    rule_set.responsable_aprobacion_ref = f'controlled-mirror-tax-rule-reviewer-at{tax_year}'
    rule_set.official_source = rule_source
    rule_set.metadata = {
        'source': 'annual_tax_controlled_mirror_run',
        'official': False,
        'ddjj_codes': list(ddjj_codes),
        'final_tax_calculation': False,
    }
    _save_validated(rule_set)

    mapping_specs = (
        (
            DestinoMapeoTributarioAnual.RLI,
            'controlled.rli.lease_revenue',
            'RLI-LEASE-REVENUE',
            {
                'source_metric': 'annual_trial_balance.resultado_ganancia_clp',
                'trial_balance_classifier': 'RLI-LEASE-REVENUE',
            },
        ),
        (
            DestinoMapeoTributarioAnual.CPT,
            'controlled.cpt.cash_asset',
            'CPT-CASH-ASSET',
            {
                'source_metric': 'annual_trial_balance.inventario_activo_clp',
                'trial_balance_classifier': 'CPT-CASH-ASSET',
            },
        ),
        (DestinoMapeoTributarioAnual.RAI, 'controlled.register.rai', 'RAI-CONTROLLED', {}),
        (DestinoMapeoTributarioAnual.SAC, 'controlled.register.sac', 'SAC-CONTROLLED', {}),
        (DestinoMapeoTributarioAnual.DDJJ, 'controlled.ddjj.package', 'DDJJ-CONTROLLED', {'ddjj_codes': list(ddjj_codes)}),
        (DestinoMapeoTributarioAnual.F22, 'controlled.f22.preview', 'F22-CONTROLLED', {}),
    )
    for destino, codigo_interno, codigo_destino, metadata_extra in mapping_specs:
        mapping_source = _ensure_official_source(
            config=config,
            tax_year=tax_year,
            key=f'mapping-{destino.lower()}',
            applies_to=destino,
        )
        mapping, _ = TaxCodeMapping.objects.get_or_create(
            rule_set=rule_set,
            destino=destino,
            codigo_interno=codigo_interno,
            codigo_destino=codigo_destino,
        )
        mapping.formula_ref = f'controlled-mirror-formula-{destino.lower()}-at{tax_year}'
        mapping.evidencia_ref = f'controlled-mirror-evidence-{destino.lower()}-at{tax_year}'
        mapping.official_source = mapping_source
        mapping.metadata = {
            'source': 'annual_tax_controlled_mirror_run',
            'final_tax_calculation': False,
            **metadata_extra,
        }
        _save_validated(mapping)
    return rule_set


def _ensure_ddjj_layouts(
    *,
    config: ConfiguracionFiscalEmpresa,
    tax_year: int,
    ddjj_codes: tuple[str, ...],
) -> int:
    created_or_updated = 0
    for form_code in ddjj_codes:
        media_source = _ensure_official_source(
            config=config,
            tax_year=tax_year,
            key=f'ddjj-media-{form_code}',
            applies_to=DestinoMapeoTributarioAnual.DDJJ,
        )
        form_source = _ensure_official_source(
            config=config,
            tax_year=tax_year,
            key=f'ddjj-form-{form_code}',
            applies_to=DestinoMapeoTributarioAnual.DDJJ,
        )
        layout, _ = AnnualTaxDDJJFormLayout.objects.get_or_create(
            anio_tributario=tax_year,
            form_code=str(form_code),
        )
        layout.title = f'DDJJ {form_code} AT{tax_year} preview controlado'
        layout.periodicidad = 'Anual'
        layout.allows_electronic_form = True
        layout.allows_file_importer = True
        layout.allows_file_upload = False
        layout.allows_commercial_software = True
        layout.allows_assistant = False
        layout.medio_preferente = MedioAnnualTaxDDJJ.FILE_IMPORTER
        layout.due_date_label = f'AT{tax_year}-plazo-ddjj-{form_code}-controlado'
        layout.certificate_code = f'cert-ddjj-{form_code}'
        layout.certificate_due_label = f'AT{tax_year}-plazo-certificado-{form_code}-controlado'
        layout.resolution_ref = f'controlled-mirror-resolution-ddjj-{form_code}-at{tax_year}'
        layout.declaration_status = 'preview_controlado_revisable'
        layout.layout_ref = f'controlled-mirror-layout-ddjj-{form_code}-at{tax_year}'
        layout.instructions_ref = f'controlled-mirror-instructions-ddjj-{form_code}-at{tax_year}'
        layout.responsible_ref = f'controlled-mirror-ddjj-layout-reviewer-at{tax_year}'
        layout.official_media_source = media_source
        layout.official_form_source = form_source
        layout.official_software_source = None
        layout.warnings = []
        layout.source_payload = {
            'source': 'annual_tax_controlled_mirror_run',
            'form_code': str(form_code),
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
        }
        layout.estado = EstadoAnnualTaxDDJJLayout.PREPARED
        layout.hash_layout = layout.compute_hash_layout()
        _save_validated(layout)
        created_or_updated += 1
    return created_or_updated


def _ensure_f22_layout(*, config: ConfiguracionFiscalEmpresa, tax_year: int) -> AnnualTaxF22ExportLayout:
    certification_source = _ensure_official_source(
        config=config,
        tax_year=tax_year,
        key='f22-export-format',
        applies_to=DestinoMapeoTributarioAnual.F22,
        metadata_extra={'f22_export_format': True, 'f22_certification': False},
    )
    instructions_source = _ensure_official_source(
        config=config,
        tax_year=tax_year,
        key='f22-instructions',
        applies_to=DestinoMapeoTributarioAnual.F22,
        metadata_extra={'f22_instructions': True},
    )
    layout, _ = AnnualTaxF22ExportLayout.objects.get_or_create(
        anio_tributario=tax_year,
        form_code='F22',
    )
    layout.title = f'F22 AT{tax_year} preview controlado'
    layout.allows_local_preview = True
    layout.allows_certified_file = False
    layout.allows_supervised_portal = False
    layout.medio_preferente = MedioAnnualTaxF22Export.LOCAL_PREVIEW
    layout.certification_ref = f'controlled-mirror-certification-f22-at{tax_year}'
    layout.format_ref = f'controlled-mirror-f22-layout-at{tax_year}'
    layout.instructions_ref = f'controlled-mirror-f22-instructions-at{tax_year}'
    layout.responsible_ref = f'controlled-mirror-f22-layout-reviewer-at{tax_year}'
    layout.official_certification_source = certification_source
    layout.official_instructions_source = instructions_source
    layout.warnings = []
    layout.source_payload = {
        'source': 'annual_tax_controlled_mirror_run',
        'form_code': 'F22',
        'official_format': False,
        'sii_submission': False,
        'final_tax_calculation': False,
    }
    layout.estado = EstadoAnnualTaxF22ExportLayout.PREPARED
    layout.hash_layout = layout.compute_hash_layout()
    _save_validated(layout)
    return layout


def _ensure_real_estate_source(*, config: ConfiguracionFiscalEmpresa, tax_year: int) -> AnnualTaxOfficialSource:
    return _ensure_official_source(
        config=config,
        tax_year=tax_year,
        key='real-estate-contributions',
        applies_to=DestinoMapeoTributarioAnual.F22,
        metadata_extra={
            'real_estate_contributions': True,
            'values_by_property_id': {},
            'requires_review': True,
        },
    )


def _ensure_controlled_accounts(empresa) -> tuple[CuentaContable, CuentaContable]:
    revenue_account, _ = CuentaContable.objects.get_or_create(
        empresa=empresa,
        plan_cuentas_version='ac2024-controlled-mirror',
        codigo='4100',
        defaults={
            'nombre': 'Ingresos por arriendo controlados',
            'naturaleza': NaturalezaCuenta.CREDIT,
            'nivel': 1,
            'estado': 'activa',
        },
    )
    asset_account, _ = CuentaContable.objects.get_or_create(
        empresa=empresa,
        plan_cuentas_version='ac2024-controlled-mirror',
        codigo='1100',
        defaults={
            'nombre': 'Banco/caja controlado',
            'naturaleza': NaturalezaCuenta.DEBIT,
            'nivel': 1,
            'estado': 'activa',
        },
    )
    return revenue_account, asset_account


def _annual_ledger_haber_total(empresa, commercial_year: int) -> Decimal:
    total = Decimal('0.00')
    for item in LibroDiario.objects.filter(empresa=empresa, periodo__startswith=f'{commercial_year}-'):
        summary = item.resumen if isinstance(item.resumen, dict) else {}
        total += _decimal(summary.get('total_haber'))
    return total


def _ensure_annual_trial_balance_source(empresa, commercial_year: int, tax_year: int) -> BalanceComprobacion:
    period = f'{commercial_year}-12'
    balance, _ = BalanceComprobacion.objects.get_or_create(
        empresa=empresa,
        periodo=period,
        defaults={
            'estado_snapshot': EstadoCierreMensual.APPROVED,
            'storage_ref': f'ac2024-controlled-annual-balance-{empresa.pk}-{commercial_year}',
            'resumen': {},
        },
    )
    revenue_account, asset_account = _ensure_controlled_accounts(empresa)
    existing_summary = balance.resumen if isinstance(balance.resumen, dict) else {}
    annual_revenue = _annual_ledger_haber_total(empresa, commercial_year)
    december_balance_total = _decimal(existing_summary.get('total_debe'))
    if december_balance_total == Decimal('0.00'):
        december_balance_total = annual_revenue
    line_items = [
        {
            'codigo_cuenta': revenue_account.codigo,
            'clasificador_dj1847': 'RLI-LEASE-REVENUE',
            'sumas_haber_clp': str(annual_revenue),
            'saldo_acreedor_clp': str(annual_revenue),
            'resultado_ganancia_clp': str(annual_revenue),
            'formula_ref': f'ac2024-controlled-rli-preview-at{tax_year}',
            'evidencia_ref': f'ac2024-controlled-ledger-haber-at{tax_year}',
        },
        {
            'codigo_cuenta': asset_account.codigo,
            'clasificador_dj1847': 'CPT-CASH-ASSET',
            'sumas_debe_clp': str(december_balance_total),
            'saldo_deudor_clp': str(december_balance_total),
            'inventario_activo_clp': str(december_balance_total),
            'formula_ref': f'ac2024-controlled-cpt-preview-at{tax_year}',
            'evidencia_ref': f'ac2024-controlled-december-balance-at{tax_year}',
        },
    ]
    balance.estado_snapshot = EstadoCierreMensual.APPROVED
    balance.storage_ref = balance.storage_ref or f'ac2024-controlled-annual-balance-{empresa.pk}-{commercial_year}'
    balance.resumen = {
        **existing_summary,
        'controlled_annual_mirror': True,
        'lineas_balance_8_columnas': line_items,
        'lineas_balance_8_columnas_source': 'annual_tax_controlled_mirror_run',
        'source_limitations': [
            'controlled_preview_requires_expert_review',
            'not_final_tax_calculation',
        ],
        'final_tax_calculation': False,
    }
    _save_validated(balance)
    return balance


def run_annual_tax_controlled_mirror(
    *,
    empresa,
    commercial_year: int,
    tax_year: int,
    source_label: str,
    authorization_ref: str,
    responsible_ref: str,
    fiscal_rule_ref: str,
    certificates_proof_ref: str,
    write_database: bool = False,
    ddjj_codes: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    if tax_year != commercial_year + 1:
        raise ValueError('tax_year debe ser commercial_year + 1.')
    refs = {
        'source_label': source_label,
        'authorization_ref': authorization_ref,
        'responsible_ref': responsible_ref,
        'fiscal_rule_ref': fiscal_rule_ref,
        'certificates_proof_ref': certificates_proof_ref,
    }
    for field_name in REQUIRED_REFERENCES:
        refs[field_name] = _require_reference(refs[field_name], field_name)

    config = _active_fiscal_config(empresa)
    facts = _normalized_monthly_facts(empresa, commercial_year)
    fact_months = sorted({fact.mes for fact in facts})
    blockers = []
    if fact_months != list(range(1, 13)):
        blockers.append('monthly_tax_facts_incomplete_12_months')

    selected_ddjj_codes = tuple(
        str(code).strip()
        for code in (ddjj_codes or tuple(config.ddjj_habilitadas or ()) or DEFAULT_DDJJ_CODES)
        if str(code).strip()
    )

    result: dict[str, Any] = {
        'schema_version': CONTROLLED_MIRROR_RUN_SCHEMA_VERSION,
        'writes_database': bool(write_database),
        'empresa_id': empresa.id,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_label': refs['source_label'],
        'monthly_tax_fact_months': fact_months,
        'monthly_tax_facts_total': len(facts),
        'ddjj_codes': list(selected_ddjj_codes),
        'blockers': list(blockers),
        'ready_for_generation': not blockers,
        'generated': False,
        'safety': {
            'uses_real_sii': False,
            'uses_external_auth': False,
            'uses_expected_outputs_as_inputs': False,
            'final_tax_calculation': False,
        },
    }
    if blockers or not write_database:
        return result

    with transaction.atomic():
        if selected_ddjj_codes and tuple(config.ddjj_habilitadas or ()) != selected_ddjj_codes:
            config.ddjj_habilitadas = list(selected_ddjj_codes)
            config.save(update_fields=['ddjj_habilitadas', 'updated_at'])

        _ensure_capability(
            empresa,
            CapacidadSII.DDJJ_PREPARACION,
            ref_prefix=refs['certificates_proof_ref'],
            fiscal_rule_ref=refs['fiscal_rule_ref'],
        )
        _ensure_capability(
            empresa,
            CapacidadSII.F22_PREPARACION,
            ref_prefix=refs['certificates_proof_ref'],
            fiscal_rule_ref=refs['fiscal_rule_ref'],
        )
        rule_set = _ensure_tax_year_ruleset(
            config=config,
            tax_year=tax_year,
            ddjj_codes=selected_ddjj_codes,
            fiscal_rule_ref=refs['fiscal_rule_ref'],
        )
        _ensure_ddjj_layouts(config=config, tax_year=tax_year, ddjj_codes=selected_ddjj_codes)
        _ensure_f22_layout(config=config, tax_year=tax_year)
        _ensure_real_estate_source(config=config, tax_year=tax_year)
        balance = _ensure_annual_trial_balance_source(empresa, commercial_year, tax_year)
        source_bundle = freeze_annual_tax_source_bundle(
            empresa,
            tax_year,
            config,
            rule_set,
            source_kind=SourceKindRentaAnual.CONTROLLED_SNAPSHOT,
            source_label=refs['source_label'],
            authorization_ref=refs['authorization_ref'],
            responsible_ref=refs['responsible_ref'],
        )
        process, ddjj, f22 = generate_annual_preparation(empresa, tax_year)

    result.update(
        {
            'generated': True,
            'process_id': process.id,
            'process_state': process.estado,
            'source_bundle_id': source_bundle.id,
            'source_bundle_kind': source_bundle.source_kind,
            'source_bundle_monthly_tax_fact_months': source_bundle.resumen_fuentes.get('monthly_tax_fact_months'),
            'source_bundle_obligation_months': source_bundle.resumen_fuentes.get('obligation_months'),
            'annual_trial_balance_source_id': balance.id,
            'ddjj_id': ddjj.id,
            'ddjj_state': ddjj.estado_preparacion,
            'f22_id': f22.id,
            'f22_state': f22.estado_preparacion,
        }
    )
    return result
