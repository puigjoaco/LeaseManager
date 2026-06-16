from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from contabilidad.models import EstadoPreparacionTributaria
from core.annual_tax_controlled_load_plan import COMPARISON_ONLY_CATEGORIES
from core.annual_tax_expected_output_content import (
    DOCUMENT_SEMANTIC_CATEGORIES,
    canonical_generated_clp_amount_token,
    extract_expected_output_content_signals,
    extract_expected_output_document_semantic_signals,
    extract_expected_output_value_signals,
    value_ref_for_clp_amount_token,
)
from core.annual_tax_source_manifest import EXPECTED_DDJJ_FORMS, EXPECTED_ANNUAL_TAX_REGISTER_KEYS
from core.reference_validation import redact_sensitive_reference
from sii.models import (
    AnnualEnterpriseRegisterSet,
    AnnualEnterpriseRegisterMovement,
    AnnualTaxArtifactMatrix,
    AnnualTaxDossier,
    AnnualTaxDDJJFormLayout,
    AnnualTaxExport,
    AnnualTaxF22ExportLayout,
    AnnualTaxReviewChecklist,
    AnnualTaxTrialBalance,
    AnnualTaxTrialBalanceLine,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    DDJJPreparacionAnual,
    EstadoAnnualEnterpriseRegister,
    EstadoAnnualTaxDDJJLayout,
    EstadoAnnualTaxArtifactReview,
    EstadoAnnualTaxDossier,
    EstadoAnnualTaxExport,
    EstadoAnnualTaxF22ExportLayout,
    EstadoAnnualTaxReviewChecklist,
    EstadoAnnualTaxTrialBalance,
    EstadoAnnualTaxWorkbook,
    F22PreparacionAnual,
    ProcesoRentaAnual,
    TipoAnnualEnterpriseRegister,
    TipoAnnualTaxWorkbook,
)


EXPECTED_OUTPUT_COMPARISON_SCHEMA_VERSION = 'annual-tax-expected-output-comparison.v1'

REGISTER_KEY_TARGETS = {
    'capital_propio': {'workbooks': {TipoAnnualTaxWorkbook.CPT}, 'enterprise_registers': set()},
    'razonabilidad_cpt': {'workbooks': {TipoAnnualTaxWorkbook.CPT}, 'enterprise_registers': set()},
    'renta_liquida': {'workbooks': {TipoAnnualTaxWorkbook.RLI}, 'enterprise_registers': set()},
    'determinacion_rai': {'workbooks': set(), 'enterprise_registers': {TipoAnnualEnterpriseRegister.RAI}},
    'rentas_empresariales': {
        'workbooks': set(),
        'enterprise_registers': {
            TipoAnnualEnterpriseRegister.RAI,
            TipoAnnualEnterpriseRegister.SAC,
            TipoAnnualEnterpriseRegister.RETIROS,
            TipoAnnualEnterpriseRegister.DIVIDENDOS,
        },
    },
}


def _normalize_forms(values: Any) -> list[str]:
    forms = set()
    for value in values or []:
        normalized = str(value or '').strip()
        if normalized:
            forms.add(normalized)
    return sorted(forms)


def _files_by_category(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in manifest.get('files') or []:
        category = str(item.get('category') or '').strip()
        if category in COMPARISON_ONLY_CATEGORIES:
            grouped[category].append(item)
    return dict(grouped)


def _artifact_keys(files: list[dict[str, Any]]) -> list[str]:
    keys = {
        str(item.get('artifact_key') or '').strip()
        for item in files
        if str(item.get('artifact_key') or '').strip()
    }
    return sorted(keys)


def _expected_ddjj_forms(files: list[dict[str, Any]]) -> list[str]:
    forms = set()
    for item in files:
        if str(item.get('output_status') or '').strip() != 'accepted':
            continue
        for form in item.get('ddjj_forms') or []:
            normalized = str(form or '').strip()
            if normalized:
                forms.add(normalized)
    return sorted(forms)


def _generated_process(empresa, tax_year: int) -> ProcesoRentaAnual | None:
    return (
        ProcesoRentaAnual.objects.filter(empresa=empresa, anio_tributario=tax_year)
        .select_related('source_bundle')
        .first()
    )


def _safe_reference(value: Any) -> str:
    return redact_sensitive_reference(value)


def _hash_or_blank(value: Any) -> str:
    text = str(value or '').strip()
    return text if len(text) == 64 else ''


def _generated_artifact_evidence(
    *,
    process: ProcesoRentaAnual,
    trial_balances,
    workbooks,
    registers,
    ddjj: DDJJPreparacionAnual | None,
    f22: F22PreparacionAnual | None,
    matrix: AnnualTaxArtifactMatrix | None,
    dossier: AnnualTaxDossier | None,
    annual_export: AnnualTaxExport | None,
    checklist: AnnualTaxReviewChecklist | None,
) -> dict[str, Any]:
    source_bundle = process.source_bundle
    evidence = {
        'process': {
            'process_id': process.id,
            'process_state': process.estado,
            'source_bundle_id': process.source_bundle_id,
            'source_bundle_hash': _hash_or_blank(getattr(source_bundle, 'hash_fuentes', '')),
            'ddjj_package_ref': _safe_reference(process.paquete_ddjj_ref),
            'f22_draft_ref': _safe_reference(process.borrador_f22_ref),
        },
        'trial_balances': [
            {
                'id': item.id,
                'source_bundle_id': item.source_bundle_id,
                'rule_set_id': item.rule_set_id,
                'official_source_id': item.official_source_id,
                'source_balance_id': item.source_balance_id,
                'periodo_cierre': item.periodo_cierre,
                'source_ref': _safe_reference(item.source_ref),
                'lines_total': item.lines_total,
                'warnings_total': item.warnings_total,
                'hash_balance': _hash_or_blank(item.hash_balance),
            }
            for item in trial_balances
        ],
        'workbooks_by_type': {
            str(item.tipo): {
                'id': item.id,
                'source_bundle_id': item.source_bundle_id,
                'rule_set_id': item.rule_set_id,
                'source_ref': _safe_reference(item.source_ref),
                'lines_total': item.lines.count(),
                'hash_workbook': _hash_or_blank(item.hash_workbook),
            }
            for item in workbooks
        },
        'enterprise_registers_by_type': {
            str(item.tipo_registro): {
                'id': item.id,
                'source_bundle_id': item.source_bundle_id,
                'rule_set_id': item.rule_set_id,
                'source_ref': _safe_reference(item.source_ref),
                'movements_total': item.movements.count(),
                'hash_registro': _hash_or_blank(item.hash_registro),
            }
            for item in registers
        },
        'ddjj': {
            'id': ddjj.id,
            'estado_preparacion': ddjj.estado_preparacion,
            'paquete_ref': _safe_reference(ddjj.paquete_ref),
        }
        if ddjj
        else None,
        'f22': {
            'id': f22.id,
            'estado_preparacion': f22.estado_preparacion,
            'borrador_ref': _safe_reference(f22.borrador_ref),
        }
        if f22
        else None,
        'artifact_matrix': {
            'id': matrix.id,
            'source_bundle_id': matrix.source_bundle_id,
            'rule_set_id': matrix.rule_set_id,
            'items_total': matrix.items_total,
            'ddjj_items_total': matrix.ddjj_items_total,
            'f22_items_total': matrix.f22_items_total,
            'warnings_total': int(
                (matrix.resumen_matriz if isinstance(matrix.resumen_matriz, dict) else {}).get(
                    'warnings_total',
                    0,
                )
                or 0
            ),
            'warnings_pending_review_total': int(
                (matrix.resumen_matriz if isinstance(matrix.resumen_matriz, dict) else {}).get(
                    'warnings_pending_review_total',
                    0,
                )
                or 0
            ),
            'review_state_counts': (
                matrix.resumen_matriz.get('review_state_counts', {})
                if isinstance(matrix.resumen_matriz, dict)
                else {}
            ),
            'hash_matriz': _hash_or_blank(matrix.hash_matriz),
        }
        if matrix
        else None,
        'dossier': {
            'id': dossier.id,
            'artifact_matrix_id': dossier.artifact_matrix_id,
            'dossier_ref': _safe_reference(dossier.dossier_ref),
            'review_state': dossier.review_state,
            'warnings_total': dossier.warnings_total,
            'hash_dossier': _hash_or_blank(dossier.hash_dossier),
        }
        if dossier
        else None,
        'annual_export': {
            'id': annual_export.id,
            'dossier_id': annual_export.dossier_id,
            'artifact_matrix_id': annual_export.artifact_matrix_id,
            'export_ref': _safe_reference(annual_export.export_ref),
            'review_state': annual_export.review_state,
            'target_items_total': annual_export.target_items_total,
            'ddjj_items_total': annual_export.ddjj_items_total,
            'f22_items_total': annual_export.f22_items_total,
            'warnings_total': annual_export.warnings_total,
            'official_format': annual_export.official_format,
            'sii_submission': annual_export.sii_submission,
            'final_tax_calculation': annual_export.final_tax_calculation,
            'hash_export': _hash_or_blank(annual_export.hash_export),
        }
        if annual_export
        else None,
        'review_checklist': {
            'id': checklist.id,
            'dossier_id': checklist.dossier_id,
            'annual_export_id': checklist.annual_export_id,
            'artifact_matrix_id': checklist.artifact_matrix_id,
            'checklist_ref': _safe_reference(checklist.checklist_ref),
            'evidence_ref': _safe_reference(checklist.evidence_ref),
            'items_total': checklist.items_total,
            'completed_items_total': checklist.completed_items_total,
            'blockers_total': checklist.blockers_total,
            'warnings_total': checklist.warnings_total,
            'hash_checklist': _hash_or_blank(checklist.hash_checklist),
        }
        if checklist
        else None,
    }
    return evidence


def _generated_inventory(process: ProcesoRentaAnual | None) -> dict[str, Any]:
    if process is None:
        return {
            'process_present': False,
            'prepared_trial_balance_count': 0,
            'prepared_workbook_types': [],
            'prepared_enterprise_register_types': [],
            'prepared_ddjj_forms': [],
            'prepared_f22': False,
            'artifact_matrix_present': False,
            'dossier_present': False,
            'export_present': False,
            'review_checklist_present': False,
            'review_warning_counts': {},
            'review_blockers_total': 0,
            'generated_artifact_evidence': {},
        }

    trial_balances = list(
        AnnualTaxTrialBalance.objects.filter(
            proceso_renta_anual=process,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        )
    )
    workbooks = list(
        AnnualTaxWorkbook.objects.filter(
            proceso_renta_anual=process,
            estado=EstadoAnnualTaxWorkbook.PREPARED,
        )
    )
    registers = list(
        AnnualEnterpriseRegisterSet.objects.filter(
            proceso_renta_anual=process,
            estado=EstadoAnnualEnterpriseRegister.PREPARED,
        )
    )
    ddjj = DDJJPreparacionAnual.objects.filter(
        proceso_renta_anual=process,
        estado_preparacion=EstadoPreparacionTributaria.PREPARED,
    ).first()
    f22 = F22PreparacionAnual.objects.filter(
        proceso_renta_anual=process,
        estado_preparacion=EstadoPreparacionTributaria.PREPARED,
    ).first()
    matrix = AnnualTaxArtifactMatrix.objects.filter(proceso_renta_anual=process).first()
    dossier = AnnualTaxDossier.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxDossier.PREPARED,
    ).first()
    annual_export = AnnualTaxExport.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxExport.PREPARED,
    ).first()
    checklist = AnnualTaxReviewChecklist.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxReviewChecklist.PREPARED,
    ).first()

    ddjj_summary = ddjj.resumen_paquete if ddjj and isinstance(ddjj.resumen_paquete, dict) else {}
    prepared_ddjj_forms = _normalize_forms(ddjj_summary.get('ddjj_habilitadas'))

    review_warning_counts = Counter()
    review_blockers_total = 0
    if matrix is not None:
        matrix_summary = matrix.resumen_matriz if isinstance(matrix.resumen_matriz, dict) else {}
        review_warning_counts['artifact_matrix_warnings'] += int(
            matrix_summary.get('warnings_pending_review_total', matrix_summary.get('warnings_total')) or 0
        )
        review_states = matrix_summary.get('review_state_counts') if isinstance(matrix_summary, dict) else {}
        if isinstance(review_states, dict):
            review_blockers_total += int(review_states.get(EstadoAnnualTaxArtifactReview.BLOCKED) or 0)
    if dossier is not None:
        if dossier.review_state != EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW:
            review_warning_counts['dossier_warnings'] += int(dossier.warnings_total or 0)
            review_warning_counts[f'dossier_{dossier.review_state}'] += 1
    if annual_export is not None:
        if annual_export.review_state != EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW:
            review_warning_counts['export_warnings'] += int(annual_export.warnings_total or 0)
            review_warning_counts[f'export_{annual_export.review_state}'] += 1
    if checklist is not None:
        review_warning_counts['checklist_warnings'] += int(checklist.warnings_total or 0)
        review_blockers_total += int(checklist.blockers_total or 0)

    return {
        'process_present': True,
        'process_id': process.id,
        'process_state': process.estado,
        'source_bundle_id': process.source_bundle_id,
        'prepared_trial_balance_count': len(trial_balances),
        'prepared_workbook_types': sorted({str(item.tipo) for item in workbooks}),
        'prepared_enterprise_register_types': sorted({str(item.tipo_registro) for item in registers}),
        'prepared_ddjj_forms': prepared_ddjj_forms,
        'prepared_f22': f22 is not None,
        'artifact_matrix_present': matrix is not None,
        'dossier_present': dossier is not None,
        'export_present': annual_export is not None,
        'review_checklist_present': checklist is not None,
        'review_warning_counts': dict(sorted((key, value) for key, value in review_warning_counts.items() if value)),
        'review_blockers_total': review_blockers_total,
        'generated_artifact_evidence': _generated_artifact_evidence(
            process=process,
            trial_balances=trial_balances,
            workbooks=workbooks,
            registers=registers,
            ddjj=ddjj,
            f22=f22,
            matrix=matrix,
            dossier=dossier,
            annual_export=annual_export,
            checklist=checklist,
        ),
    }


def _compare_balance(expected_files: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    expected = bool(expected_files)
    generated = int(inventory['prepared_trial_balance_count']) > 0
    return {
        'expected': expected,
        'expected_files': len(expected_files),
        'expected_artifact_keys': _artifact_keys(expected_files),
        'generated': generated,
        'generated_count': inventory['prepared_trial_balance_count'],
        'matched': not expected or generated,
    }


def _compare_registers(expected_files: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    expected_keys = _artifact_keys(expected_files)
    generated_workbooks = set(inventory['prepared_workbook_types'])
    generated_registers = set(inventory['prepared_enterprise_register_types'])
    by_key = {}
    missing = []
    for key in expected_keys:
        spec = REGISTER_KEY_TARGETS.get(key, {'workbooks': set(), 'enterprise_registers': set()})
        required_workbooks = {str(value) for value in spec['workbooks']}
        required_registers = {str(value) for value in spec['enterprise_registers']}
        missing_workbooks = sorted(required_workbooks - generated_workbooks)
        missing_registers = sorted(required_registers - generated_registers)
        matched = not missing_workbooks and not missing_registers
        by_key[key] = {
            'required_workbooks': sorted(required_workbooks),
            'required_enterprise_registers': sorted(required_registers),
            'missing_workbooks': missing_workbooks,
            'missing_enterprise_registers': missing_registers,
            'matched': matched,
        }
        if not matched:
            missing.append(key)
    return {
        'expected_artifact_keys': expected_keys,
        'generated_workbook_types': sorted(generated_workbooks),
        'generated_enterprise_register_types': sorted(generated_registers),
        'by_key': by_key,
        'missing_artifact_keys': sorted(missing),
        'matched': not missing,
    }


def _compare_ddjj(expected_files: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    expected_forms = _expected_ddjj_forms(expected_files)
    generated_forms = set(inventory['prepared_ddjj_forms'])
    missing_forms = sorted(set(expected_forms) - generated_forms)
    unexpected_forms = sorted(generated_forms - set(EXPECTED_DDJJ_FORMS))
    return {
        'expected_forms': expected_forms,
        'generated_forms': sorted(generated_forms),
        'missing_forms': missing_forms,
        'unexpected_forms': unexpected_forms,
        'matched': not missing_forms,
    }


def _compare_f22(expected_files: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    expected = bool(expected_files)
    generated = bool(inventory['prepared_f22'])
    return {
        'expected': expected,
        'expected_files': len(expected_files),
        'expected_artifact_keys': _artifact_keys(expected_files),
        'generated': generated,
        'matched': not expected or generated,
    }


def _value_target(
    *,
    target_key: str,
    category: str,
    artifact_key: str,
    semantic_key: str,
    value: Any,
) -> dict[str, Any] | None:
    amount_token = canonical_generated_clp_amount_token(value)
    if not amount_token:
        return None
    return {
        'target_key': target_key,
        'category': category,
        'artifact_key': artifact_key,
        'semantic_key': semantic_key,
        'amount_token': amount_token,
        'amount_ref': value_ref_for_clp_amount_token(amount_token),
    }


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        return []
    normalized = []
    for item in items:
        text = str(item or '').strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _configured_artifacts(source_payload: Any, default_artifacts: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(source_payload, dict) or 'expected_output_artifacts' not in source_payload:
        return default_artifacts
    return tuple(_string_list(source_payload.get('expected_output_artifacts')))


def _generated_value_targets(process: ProcesoRentaAnual | None) -> list[dict[str, Any]]:
    if process is None:
        return []

    targets: list[dict[str, Any]] = []
    for line in AnnualTaxTrialBalanceLine.objects.filter(
        trial_balance__proceso_renta_anual=process,
    ).order_by('codigo_cuenta'):
        for field_name in (
            'sumas_debe_clp',
            'sumas_haber_clp',
            'saldo_deudor_clp',
            'saldo_acreedor_clp',
            'inventario_activo_clp',
            'inventario_pasivo_clp',
            'resultado_perdida_clp',
            'resultado_ganancia_clp',
        ):
            target = _value_target(
                target_key=f'trial_balance:{line.codigo_cuenta}:{field_name}',
                category='annual_balance_expected_output',
                artifact_key='balance_general',
                semantic_key=f'annual_trial_balance.{field_name}',
                value=getattr(line, field_name),
            )
            if target:
                targets.append(target)

    workbook_artifacts = {
        TipoAnnualTaxWorkbook.CPT: ('capital_propio', 'razonabilidad_cpt'),
        TipoAnnualTaxWorkbook.RLI: ('renta_liquida',),
    }
    for line in AnnualTaxWorkbookLine.objects.filter(
        workbook__proceso_renta_anual=process,
    ).select_related('workbook').order_by('workbook__tipo', 'codigo_destino'):
        artifact_keys = _configured_artifacts(
            line.source_payload,
            workbook_artifacts.get(line.workbook.tipo, ()),
        )
        for artifact_key in artifact_keys:
            target = _value_target(
                target_key=f'workbook:{line.workbook.tipo}:{line.codigo_destino}',
                category='annual_tax_register_expected_output',
                artifact_key=artifact_key,
                semantic_key=f'annual_tax_workbook.{line.workbook.tipo}.monto_clp',
                value=line.monto_clp,
            )
            if target:
                targets.append(target)

    register_artifacts = {
        TipoAnnualEnterpriseRegister.RAI: ('determinacion_rai', 'rentas_empresariales'),
        TipoAnnualEnterpriseRegister.SAC: ('rentas_empresariales',),
        TipoAnnualEnterpriseRegister.RETIROS: ('rentas_empresariales',),
        TipoAnnualEnterpriseRegister.DIVIDENDOS: ('rentas_empresariales',),
    }
    for movement in AnnualEnterpriseRegisterMovement.objects.filter(
        register_set__proceso_renta_anual=process,
    ).select_related('register_set', 'source_workbook_line').order_by(
        'register_set__tipo_registro',
        'codigo_interno',
    ):
        artifact_keys = _configured_artifacts(
            movement.source_payload,
            register_artifacts.get(movement.register_set.tipo_registro, ()),
        )
        for artifact_key in artifact_keys:
            target = _value_target(
                target_key=f'enterprise_register:{movement.register_set.tipo_registro}:{movement.codigo_interno}',
                category='annual_tax_register_expected_output',
                artifact_key=artifact_key,
                semantic_key=f'annual_enterprise_register.{movement.register_set.tipo_registro}.monto_clp',
                value=movement.monto_clp,
            )
            if target:
                targets.append(target)
    return targets


def _generated_document_targets(process: ProcesoRentaAnual | None) -> list[dict[str, Any]]:
    if process is None:
        return []

    targets: list[dict[str, Any]] = []
    ddjj = DDJJPreparacionAnual.objects.filter(
        proceso_renta_anual=process,
        estado_preparacion=EstadoPreparacionTributaria.PREPARED,
    ).first()
    ddjj_summary = ddjj.resumen_paquete if ddjj and isinstance(ddjj.resumen_paquete, dict) else {}
    ddjj_forms = _normalize_forms(ddjj_summary.get('ddjj_habilitadas'))
    prepared_layouts = {
        layout.form_code: layout
        for layout in AnnualTaxDDJJFormLayout.objects.filter(
            anio_tributario=process.anio_tributario,
            form_code__in=ddjj_forms,
            estado=EstadoAnnualTaxDDJJLayout.PREPARED,
        )
    }
    for form in ddjj_forms:
        layout = prepared_layouts.get(form)
        targets.append(
            {
                'target_key': f'ddjj:{form}',
                'category': 'ddjj_expected_output',
                'artifact_key': f'dj_{form}',
                'form': form,
                'prepared': ddjj is not None,
                'layout_prepared': layout is not None,
                'layout_medium': layout.medio_preferente if layout else '',
            }
        )

    f22 = F22PreparacionAnual.objects.filter(
        proceso_renta_anual=process,
        estado_preparacion=EstadoPreparacionTributaria.PREPARED,
    ).first()
    f22_layout = AnnualTaxF22ExportLayout.objects.filter(
        anio_tributario=process.anio_tributario,
        form_code='F22',
        estado=EstadoAnnualTaxF22ExportLayout.PREPARED,
    ).first()
    if f22 is not None:
        targets.append(
            {
                'target_key': 'f22:F22',
                'category': 'f22_expected_output',
                'artifact_key': 'f22',
                'form': 'F22',
                'prepared': True,
                'layout_prepared': f22_layout is not None,
                'layout_medium': f22_layout.medio_preferente if f22_layout else '',
            }
        )
    return targets


def compare_annual_tax_expected_outputs(
    *,
    empresa,
    commercial_year: int,
    tax_year: int,
    manifest: dict[str, Any],
    source_root: Path | None = None,
) -> dict[str, Any]:
    if tax_year != commercial_year + 1:
        raise ValueError('tax_year debe ser commercial_year + 1.')

    grouped = _files_by_category(manifest)
    process = _generated_process(empresa, tax_year)
    inventory = _generated_inventory(process)
    matches = {
        'annual_balance_expected_output': _compare_balance(
            grouped.get('annual_balance_expected_output', []),
            inventory,
        ),
        'annual_tax_register_expected_output': _compare_registers(
            grouped.get('annual_tax_register_expected_output', []),
            inventory,
        ),
        'ddjj_expected_output': _compare_ddjj(grouped.get('ddjj_expected_output', []), inventory),
        'f22_expected_output': _compare_f22(grouped.get('f22_expected_output', []), inventory),
    }
    coverage_match_keys = tuple(matches.keys())

    content_signals = None
    content_identity_ready = False
    document_semantic_signals = None
    document_semantic_ready = False
    value_signals = None
    value_equality_extractors_ready = False
    generated_document_targets = _generated_document_targets(process)
    generated_value_targets = _generated_value_targets(process)
    if source_root is not None:
        content_signals = extract_expected_output_content_signals(source_root=source_root, manifest=manifest)
        content_summary = content_signals['summary']
        content_ddjj_forms = set(content_summary['accepted_ddjj_forms_from_content'])
        generated_forms = set(inventory['prepared_ddjj_forms'])
        matches['ddjj_content_identity'] = {
            'expected_forms_from_content': sorted(content_ddjj_forms),
            'generated_forms': sorted(generated_forms),
            'missing_forms': sorted(content_ddjj_forms - generated_forms),
            'accepted_folios_by_form': content_summary['accepted_ddjj_folios_by_form'],
            'matched': bool(content_ddjj_forms) and not (content_ddjj_forms - generated_forms),
        }
        matches['f22_content_identity'] = {
            'expected_folios_from_content': content_summary['f22_folios_from_content'],
            'generated_f22_present': bool(inventory['prepared_f22']),
            'official_folio_generated': False,
            'matched': bool(content_summary['f22_folios_from_content']) and bool(inventory['prepared_f22']),
        }
        matches['annual_balance_content_identity'] = {
            'expected_text_extractable': bool(content_summary['balance_text_extractable']),
            'generated_trial_balance_present': int(inventory['prepared_trial_balance_count']) > 0,
            'matched': bool(content_summary['balance_text_extractable'])
            and int(inventory['prepared_trial_balance_count']) > 0,
        }
        matches['annual_tax_register_content_identity'] = {
            'expected_register_keys_with_text': content_summary['annual_tax_register_keys_with_text'],
            'generated_workbook_types': inventory['prepared_workbook_types'],
            'generated_enterprise_register_types': inventory['prepared_enterprise_register_types'],
            'missing_expected_register_text': sorted(
                set(EXPECTED_ANNUAL_TAX_REGISTER_KEYS) - set(content_summary['annual_tax_register_keys_with_text'])
            ),
            'matched': set(content_summary['annual_tax_register_keys_with_text'])
            >= set(EXPECTED_ANNUAL_TAX_REGISTER_KEYS),
        }
        content_identity_ready = (
            bool(content_summary['identity_signals_ready'])
            and matches['ddjj_content_identity']['matched']
            and matches['f22_content_identity']['matched']
            and matches['annual_balance_content_identity']['matched']
            and matches['annual_tax_register_content_identity']['matched']
        )
        document_semantic_signals = extract_expected_output_document_semantic_signals(
            source_root=source_root,
            manifest=manifest,
            generated_targets=generated_document_targets,
        )
        document_semantic_summary = document_semantic_signals['summary']
        document_semantic_ready = bool(document_semantic_summary['document_semantic_ready'])
        matches['expected_output_document_semantics'] = {
            'supported_categories': document_semantic_signals['supported_categories'],
            'generated_targets_total': document_semantic_summary['generated_targets_total'],
            'compared_documents_total': document_semantic_summary['compared_documents_total'],
            'matched_documents_total': document_semantic_summary['matched_documents_total'],
            'missing_documents_total': document_semantic_summary['missing_documents_total'],
            'document_semantic_ready': document_semantic_ready,
            'matched': document_semantic_ready,
        }
        value_signals = extract_expected_output_value_signals(
            source_root=source_root,
            manifest=manifest,
            generated_targets=generated_value_targets,
            semantic_supported_categories=DOCUMENT_SEMANTIC_CATEGORIES
            if document_semantic_ready
            else set(),
        )
        value_summary = value_signals['summary']
        value_equality_extractors_ready = bool(value_summary['value_equality_extractors_ready'])
        matches['expected_output_value_presence'] = {
            'supported_categories': value_signals['supported_categories'],
            'unsupported_expected_categories': value_signals['unsupported_expected_categories'],
            'generated_targets_total': value_summary['generated_targets_total'],
            'compared_targets_total': value_summary['compared_targets_total'],
            'matched_targets_total': value_summary['matched_targets_total'],
            'missing_targets_total': value_summary['missing_targets_total'],
            'target_value_presence_ready': value_summary['target_value_presence_ready'],
            'matched': value_equality_extractors_ready,
        }

    coverage_ready = bool(inventory['process_present']) and all(matches[key]['matched'] for key in coverage_match_keys)
    review_warning_counts = inventory['review_warning_counts']
    review_blockers_total = int(inventory['review_blockers_total'])

    blockers = []
    if not inventory['process_present']:
        blockers.append('annual_process_missing')
    if not all(matches[key]['matched'] for key in coverage_match_keys):
        blockers.append('expected_output_coverage_mismatch')
    if review_warning_counts or review_blockers_total:
        blockers.append('generated_artifacts_require_review')
    if source_root is None:
        blockers.append('expected_output_identity_extractors_not_run')
    elif content_signals and content_signals['summary'].get('blocking_extraction_errors_total', 0):
        blockers.append('expected_output_identity_extraction_errors')
    elif not content_identity_ready:
        blockers.append('expected_output_identity_mismatch')
    if source_root is None:
        blockers.append('expected_output_document_semantic_extractors_not_run')
    elif document_semantic_signals and document_semantic_signals['summary'].get(
        'blocking_extraction_errors_total',
        0,
    ):
        blockers.append('expected_output_document_semantic_extraction_errors')
    elif not document_semantic_ready:
        blockers.append('expected_output_document_semantic_mismatch')
    if source_root is None:
        blockers.append('expected_output_value_extractors_not_run')
    elif value_signals and value_signals['extraction_errors']:
        blockers.append('expected_output_value_extraction_errors')
    elif value_signals and value_signals['summary']['missing_targets_total']:
        blockers.append('expected_output_value_mismatch')
    if source_root is not None:
        if value_signals and value_signals['unsupported_expected_categories']:
            blockers.append('expected_output_value_extractors_partial')
        elif not value_equality_extractors_ready:
            blockers.append('expected_output_value_extractors_missing')

    return {
        'schema_version': EXPECTED_OUTPUT_COMPARISON_SCHEMA_VERSION,
        'empresa_id': empresa.id,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_manifest_hash': manifest.get('hash_manifest') or manifest.get('source_manifest_hash') or '',
        'comparison_scope': {
            'level': 'coverage_traceability_and_identity' if source_root is not None else 'coverage_and_traceability',
            'content_identity_extraction_performed': source_root is not None,
            'content_comparison_performed': source_root is not None,
            'document_semantic_extraction_performed': source_root is not None,
            'numeric_equality_performed': False,
            'categories': sorted(COMPARISON_ONLY_CATEGORIES),
        },
        'expected_targets': {
            category: {
                'files': len(files),
                'artifact_keys': _artifact_keys(files),
                'ddjj_forms': _expected_ddjj_forms(files) if category == 'ddjj_expected_output' else [],
            }
            for category, files in sorted(grouped.items())
        },
        'generated_inventory': inventory,
        'expected_output_content_signals': content_signals,
        'expected_output_document_semantic_signals': document_semantic_signals,
        'expected_output_value_signals': value_signals,
        'matches': matches,
        'summary': {
            'coverage_ready_for_content_comparison': coverage_ready,
            'content_identity_extractors_ready': content_identity_ready,
            'document_semantic_extractors_ready': document_semantic_ready,
            'value_equality_extractors_ready': value_equality_extractors_ready,
            'ready_for_mirror_conclusion': (
                coverage_ready
                and content_identity_ready
                and document_semantic_ready
                and value_equality_extractors_ready
                and not review_warning_counts
                and review_blockers_total == 0
            ),
            'blockers': blockers,
        },
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'uses_expected_outputs_as_inputs': False,
            'expected_outputs_used_as_comparison_only': True,
            'final_tax_calculation': False,
            'stores_raw_expected_output_text': False,
        },
    }
