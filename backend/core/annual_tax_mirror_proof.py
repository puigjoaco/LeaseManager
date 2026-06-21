from __future__ import annotations

from pathlib import Path
from typing import Any

from core.annual_tax_controlled_mirror_run import CONTROLLED_MIRROR_RUN_SCHEMA_VERSION
from core.annual_tax_expected_output_comparator import compare_annual_tax_expected_outputs
from core.annual_tax_ownership_patch_validator import OWNERSHIP_PATCH_VALIDATION_SCHEMA_VERSION
from core.annual_tax_ownership_review_checklist import OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION
from core.stage6_renta_anual_readiness import collect_stage6_renta_anual_readiness


ANNUAL_TAX_MIRROR_PROOF_SCHEMA_VERSION = 'annual-tax-mirror-proof.v1'
VALUE_EQUALITY_COMPLETION_CAPABILITY = 'expected_output_value_equality_completion'


def _manifest_source_ready(manifest: dict[str, Any]) -> bool:
    readiness = manifest.get('mirror_proof_readiness')
    if isinstance(readiness, dict):
        return bool(readiness.get('source_documentation_confirmed_for_ac2024_at2025'))
    coverage = manifest.get('coverage')
    if isinstance(coverage, dict):
        return bool(coverage.get('ready_for_mirror_source_bundle'))
    return False


def _manifest_architecture_ready(manifest: dict[str, Any]) -> bool:
    readiness = manifest.get('mirror_proof_readiness')
    if isinstance(readiness, dict):
        return bool(readiness.get('architecture_complete_for_mirror_run'))
    return _manifest_source_ready(manifest)


def _manifest_closed_books_pilot_ready(manifest: dict[str, Any]) -> bool:
    readiness = manifest.get('mirror_proof_readiness')
    if isinstance(readiness, dict):
        if 'ready_to_start_closed_books_pilot' in readiness:
            return bool(readiness.get('ready_to_start_closed_books_pilot'))
        if 'closed_books_pilot_ready_for_ac2024_at2025' in readiness:
            return bool(readiness.get('closed_books_pilot_ready_for_ac2024_at2025'))
    coverage = manifest.get('coverage')
    if isinstance(coverage, dict):
        if 'ready_for_closed_books_mirror_pilot' in coverage:
            return bool(coverage.get('ready_for_closed_books_mirror_pilot'))
    return _manifest_source_ready(manifest)


def _manifest_readiness_list(manifest: dict[str, Any], key: str) -> list[str]:
    readiness = manifest.get('mirror_proof_readiness')
    if not isinstance(readiness, dict):
        return []
    values = readiness.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value or '').strip()]


def _ownership_evidence_ready(ownership_evidence: dict[str, Any] | None) -> bool:
    if not isinstance(ownership_evidence, dict):
        return False

    safety = ownership_evidence.get('safety') if isinstance(ownership_evidence.get('safety'), dict) else {}
    schema_version = ownership_evidence.get('schema_version')

    if schema_version == OWNERSHIP_PATCH_VALIDATION_SCHEMA_VERSION:
        return (
            bool(ownership_evidence.get('ready_for_controlled_db_load'))
            and bool(ownership_evidence.get('ready_for_annual_generation_patch'))
            and not ownership_evidence.get('blockers')
            and safety.get('outputs_redacted') is True
            and safety.get('stores_rut_values') is False
            and safety.get('stores_person_names') is False
        )

    if schema_version == OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION:
        summary = ownership_evidence.get('summary') if isinstance(ownership_evidence.get('summary'), dict) else {}
        return (
            bool(summary.get('ready_for_controlled_db_load'))
            and bool(summary.get('ready_for_annual_generation_patch'))
            and int(summary.get('blocking_items_total') or 0) == 0
            and safety.get('stores_raw_text') is False
            and safety.get('stores_rut_values') is False
            and safety.get('stores_person_names') is False
            and safety.get('stores_source_paths') is False
        )

    return False


def _comparison_closes_value_equality_gap(comparison: dict[str, Any]) -> bool:
    summary = comparison.get('summary') if isinstance(comparison.get('summary'), dict) else {}
    blockers = {str(code) for code in summary.get('blockers') or []}
    value_blockers = {
        code for code in blockers if code.startswith('expected_output_value_')
    }
    return (
        bool(summary.get('ready_for_mirror_conclusion'))
        and bool(summary.get('value_equality_extractors_ready'))
        and not value_blockers
    )


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _sanitized_ownership_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {
            'present': False,
            'complete': False,
            'blocking_issue_code': 'ownership_snapshot_missing',
        }
    return {
        'as_of': str(snapshot.get('as_of') or ''),
        'present': bool(snapshot.get('present')),
        'participants_total': _safe_int(snapshot.get('participants_total')),
        'percentage_total': str(snapshot.get('percentage_total') or '0.00'),
        'complete': bool(snapshot.get('complete')),
        'has_duplicate_participants': bool(snapshot.get('has_duplicate_participants')),
        'blocking_issue_code': str(snapshot.get('blocking_issue_code') or ''),
    }


def _mirror_run_summary(
    *,
    mirror_run: dict[str, Any] | None,
    empresa,
    commercial_year: int,
    tax_year: int,
    source_label: str,
) -> dict[str, Any]:
    if not isinstance(mirror_run, dict):
        return {
            'present': False,
            'complete': False,
            'blockers': ['evidence_missing'],
            'ownership_snapshot': _sanitized_ownership_snapshot(None),
        }

    blockers = []
    if mirror_run.get('schema_version') != CONTROLLED_MIRROR_RUN_SCHEMA_VERSION:
        blockers.append('schema_invalid')
    if _safe_int(mirror_run.get('empresa_id')) != empresa.id:
        blockers.append('empresa_mismatch')
    if _safe_int(mirror_run.get('commercial_year')) != commercial_year:
        blockers.append('commercial_year_mismatch')
    if _safe_int(mirror_run.get('tax_year')) != tax_year:
        blockers.append('tax_year_mismatch')
    if str(mirror_run.get('source_label') or '') != source_label:
        blockers.append('source_label_mismatch')

    monthly_months = mirror_run.get('monthly_tax_fact_months')
    if monthly_months != list(range(1, 13)):
        blockers.append('monthly_tax_facts_incomplete_12_months')
    if _safe_int(mirror_run.get('monthly_tax_facts_total')) != 12:
        blockers.append('monthly_tax_facts_total_invalid')

    ownership_snapshot = _sanitized_ownership_snapshot(
        mirror_run.get('ownership_snapshot') if isinstance(mirror_run.get('ownership_snapshot'), dict) else None
    )
    if not ownership_snapshot['complete']:
        blockers.append(ownership_snapshot['blocking_issue_code'] or 'ownership_snapshot_incomplete')

    if mirror_run.get('ready_for_generation') is not True:
        blockers.append('not_ready_for_generation')
    if mirror_run.get('writes_database') is not True:
        blockers.append('database_write_not_confirmed')
    if mirror_run.get('generated') is not True:
        blockers.append('not_generated')
    if _safe_int(mirror_run.get('process_id')) <= 0:
        blockers.append('process_id_missing')
    if _safe_int(mirror_run.get('source_bundle_id')) <= 0:
        blockers.append('source_bundle_id_missing')
    if str(mirror_run.get('source_bundle_kind') or '') != 'snapshot_controlado':
        blockers.append('source_bundle_kind_invalid')
    if mirror_run.get('source_bundle_monthly_tax_fact_months') != list(range(1, 13)):
        blockers.append('source_bundle_monthly_tax_fact_months_invalid')

    safety = mirror_run.get('safety') if isinstance(mirror_run.get('safety'), dict) else {}
    if (
        safety.get('uses_real_sii') is not False
        or safety.get('uses_external_auth') is not False
        or safety.get('uses_expected_outputs_as_inputs') is not False
        or safety.get('final_tax_calculation') is not False
    ):
        blockers.append('safety_boundary_failed')

    mirror_blockers = [str(code) for code in mirror_run.get('blockers') or [] if str(code or '').strip()]
    blockers.extend(mirror_blockers)

    return {
        'present': True,
        'schema_version': str(mirror_run.get('schema_version') or ''),
        'complete': not blockers,
        'ready_for_generation': bool(mirror_run.get('ready_for_generation')),
        'writes_database': bool(mirror_run.get('writes_database')),
        'generated': bool(mirror_run.get('generated')),
        'monthly_tax_facts_total': _safe_int(mirror_run.get('monthly_tax_facts_total')),
        'monthly_tax_fact_months': monthly_months if isinstance(monthly_months, list) else [],
        'process_id_present': _safe_int(mirror_run.get('process_id')) > 0,
        'process_id': _safe_int(mirror_run.get('process_id')),
        'source_bundle_id': _safe_int(mirror_run.get('source_bundle_id')),
        'source_bundle_kind': str(mirror_run.get('source_bundle_kind') or ''),
        'source_bundle_monthly_tax_fact_months': (
            mirror_run.get('source_bundle_monthly_tax_fact_months')
            if isinstance(mirror_run.get('source_bundle_monthly_tax_fact_months'), list)
            else []
        ),
        'ownership_snapshot': ownership_snapshot,
        'blockers': sorted(set(blockers)),
    }


def _mirror_run_artifact_link_summary(
    *,
    mirror_run_summary: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    generated_inventory = (
        comparison.get('generated_inventory')
        if isinstance(comparison.get('generated_inventory'), dict)
        else {}
    )
    evidence = (
        generated_inventory.get('generated_artifact_evidence')
        if isinstance(generated_inventory.get('generated_artifact_evidence'), dict)
        else {}
    )
    process_evidence = evidence.get('process') if isinstance(evidence.get('process'), dict) else {}
    mirror_process_id = _safe_int(mirror_run_summary.get('process_id'))
    mirror_source_bundle_id = _safe_int(mirror_run_summary.get('source_bundle_id'))
    inventory_process_id = _safe_int(generated_inventory.get('process_id'))
    inventory_source_bundle_id = _safe_int(generated_inventory.get('source_bundle_id'))
    evidence_process_id = _safe_int(process_evidence.get('process_id'))
    evidence_source_bundle_id = _safe_int(process_evidence.get('source_bundle_id'))

    blockers = []
    if mirror_process_id <= 0:
        blockers.append('mirror_process_id_missing')
    if mirror_source_bundle_id <= 0:
        blockers.append('mirror_source_bundle_id_missing')
    if inventory_process_id <= 0:
        blockers.append('generated_process_id_missing')
    if inventory_source_bundle_id <= 0:
        blockers.append('generated_source_bundle_id_missing')
    if evidence_process_id <= 0:
        blockers.append('evidence_process_id_missing')
    if evidence_source_bundle_id <= 0:
        blockers.append('evidence_source_bundle_id_missing')
    if mirror_process_id and inventory_process_id and mirror_process_id != inventory_process_id:
        blockers.append('process_id_mismatch')
    if mirror_process_id and evidence_process_id and mirror_process_id != evidence_process_id:
        blockers.append('evidence_process_id_mismatch')
    if (
        mirror_source_bundle_id
        and inventory_source_bundle_id
        and mirror_source_bundle_id != inventory_source_bundle_id
    ):
        blockers.append('source_bundle_id_mismatch')
    if (
        mirror_source_bundle_id
        and evidence_source_bundle_id
        and mirror_source_bundle_id != evidence_source_bundle_id
    ):
        blockers.append('evidence_source_bundle_id_mismatch')

    return {
        'complete': not blockers,
        'mirror_process_id_present': mirror_process_id > 0,
        'mirror_source_bundle_id_present': mirror_source_bundle_id > 0,
        'generated_process_id_present': inventory_process_id > 0,
        'generated_source_bundle_id_present': inventory_source_bundle_id > 0,
        'evidence_process_id_present': evidence_process_id > 0,
        'evidence_source_bundle_id_present': evidence_source_bundle_id > 0,
        'process_id_matches_generated_artifacts': (
            mirror_process_id > 0
            and mirror_process_id == inventory_process_id
            and mirror_process_id == evidence_process_id
        ),
        'source_bundle_id_matches_generated_artifacts': (
            mirror_source_bundle_id > 0
            and mirror_source_bundle_id == inventory_source_bundle_id
            and mirror_source_bundle_id == evidence_source_bundle_id
        ),
        'blockers': sorted(set(blockers)),
    }


def _effective_source_ready(
    *,
    manifest: dict[str, Any],
    manifest_source_ready: bool,
    manifest_closed_books_pilot_ready: bool,
    ownership_evidence_ready: bool,
) -> bool:
    if manifest_source_ready:
        return True
    source_blockers = set(_manifest_readiness_list(manifest, 'source_blockers'))
    remaining_source_blockers = source_blockers - {'ownership_source_missing'}
    return (
        manifest_closed_books_pilot_ready
        and ownership_evidence_ready
        and not remaining_source_blockers
    )


def _effective_architecture_ready(
    *,
    manifest: dict[str, Any],
    effective_source_ready: bool,
    manifest_architecture_ready: bool,
    comparison_closes_value_equality_gap: bool,
) -> bool:
    if manifest_architecture_ready:
        return True
    missing_capabilities = set(_manifest_readiness_list(manifest, 'missing_capabilities'))
    remaining_capabilities = set(missing_capabilities)
    if comparison_closes_value_equality_gap:
        remaining_capabilities.discard(VALUE_EQUALITY_COMPLETION_CAPABILITY)
    return effective_source_ready and not remaining_capabilities


def _safety_ok(*, manifest: dict[str, Any], comparison: dict[str, Any]) -> bool:
    manifest_safety = manifest.get('safety') if isinstance(manifest.get('safety'), dict) else {}
    comparison_safety = comparison.get('safety') if isinstance(comparison.get('safety'), dict) else {}
    return (
        manifest_safety.get('expected_outputs_used_as_inputs') is False
        and comparison_safety.get('uses_expected_outputs_as_inputs') is False
        and comparison_safety.get('expected_outputs_used_as_comparison_only') is True
        and comparison_safety.get('uses_sii_real') is False
        and comparison_safety.get('uses_credentials') is False
        and comparison_safety.get('final_tax_calculation') is False
    )


def audit_annual_tax_mirror_proof(
    *,
    empresa,
    commercial_year: int,
    tax_year: int,
    manifest: dict[str, Any],
    source_root: Path | None,
    stage5_evidence_ref: str,
    stage4_sii_evidence_ref: str,
    fiscal_rule_ref: str,
    certificates_proof_ref: str,
    responsible_ref: str,
    source_label: str,
    authorization_ref: str,
    source_kind: str,
    ownership_evidence: dict[str, Any] | None = None,
    mirror_run: dict[str, Any] | None = None,
) -> dict[str, Any]:
    comparison = compare_annual_tax_expected_outputs(
        empresa=empresa,
        commercial_year=commercial_year,
        tax_year=tax_year,
        manifest=manifest,
        source_root=source_root,
    )
    readiness = collect_stage6_renta_anual_readiness(
        stage5_evidence_ref=stage5_evidence_ref,
        stage4_sii_evidence_ref=stage4_sii_evidence_ref,
        fiscal_rule_ref=fiscal_rule_ref,
        certificates_proof_ref=certificates_proof_ref,
        responsible_ref=responsible_ref,
        source_label=source_label,
        authorization_ref=authorization_ref,
        source_kind=source_kind,
    )

    manifest_source_ready = _manifest_source_ready(manifest)
    manifest_architecture_ready = _manifest_architecture_ready(manifest)
    manifest_closed_books_pilot_ready = _manifest_closed_books_pilot_ready(manifest)
    comparison_ready = bool(comparison['summary']['ready_for_mirror_conclusion'])
    ownership_evidence_ready = _ownership_evidence_ready(ownership_evidence)
    comparison_closes_value_equality_gap = _comparison_closes_value_equality_gap(comparison)
    effective_source_ready = _effective_source_ready(
        manifest=manifest,
        manifest_source_ready=manifest_source_ready,
        manifest_closed_books_pilot_ready=manifest_closed_books_pilot_ready,
        ownership_evidence_ready=ownership_evidence_ready,
    )
    effective_architecture_ready = _effective_architecture_ready(
        manifest=manifest,
        effective_source_ready=effective_source_ready,
        manifest_architecture_ready=manifest_architecture_ready,
        comparison_closes_value_equality_gap=comparison_closes_value_equality_gap,
    )
    stage6_ready = bool(readiness['ready_for_stage6_renta_anual'])
    safety_ok = _safety_ok(manifest=manifest, comparison=comparison)
    mirror_run_summary = _mirror_run_summary(
        mirror_run=mirror_run,
        empresa=empresa,
        commercial_year=commercial_year,
        tax_year=tax_year,
        source_label=source_label,
    )
    mirror_run_ready = bool(mirror_run_summary['complete'])
    mirror_run_artifact_link_summary = _mirror_run_artifact_link_summary(
        mirror_run_summary=mirror_run_summary,
        comparison=comparison,
    )
    mirror_run_artifact_link_ready = bool(mirror_run_artifact_link_summary['complete'])

    blockers = []
    if not manifest_closed_books_pilot_ready:
        blockers.append('closed_books_pilot_entry_not_ready')
    if not effective_source_ready:
        blockers.append('source_documentation_not_confirmed')
        blockers.extend(
            f'source.{code}' for code in _manifest_readiness_list(manifest, 'source_blockers')
        )
    if not effective_architecture_ready:
        blockers.append('architecture_not_confirmed_for_mirror_run')
        missing_capabilities = set(_manifest_readiness_list(manifest, 'missing_capabilities'))
        if comparison_closes_value_equality_gap:
            missing_capabilities.discard(VALUE_EQUALITY_COMPLETION_CAPABILITY)
        blockers.extend(
            f'architecture.{code}'
            for code in sorted(missing_capabilities)
        )
    if not comparison_ready:
        blockers.extend(f'comparison.{code}' for code in comparison['summary']['blockers'])
    if not stage6_ready:
        for issue in readiness['issues']:
            code = str(issue['code'])
            blockers.append(code if code.startswith('stage6.') else f'stage6.{code}')
    if not safety_ok:
        blockers.append('mirror_proof_safety_boundary_failed')
    if not mirror_run_ready:
        blockers.append('mirror_run_evidence_not_confirmed')
        blockers.extend(f'mirror_run.{code}' for code in mirror_run_summary['blockers'])
    if not mirror_run_artifact_link_ready:
        blockers.append('mirror_run_artifacts_not_linked')
        blockers.extend(f'mirror_run_artifact_link.{code}' for code in mirror_run_artifact_link_summary['blockers'])

    ready_for_architecture_proof = (
        comparison_ready
        and stage6_ready
        and safety_ok
        and mirror_run_ready
        and mirror_run_artifact_link_ready
    )
    ready_for_objective_completion = (
        effective_source_ready and effective_architecture_ready and ready_for_architecture_proof
    )
    ready_for_closed_books_pilot = manifest_closed_books_pilot_ready and safety_ok

    return {
        'schema_version': ANNUAL_TAX_MIRROR_PROOF_SCHEMA_VERSION,
        'empresa_id': empresa.id,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_manifest_hash': manifest.get('hash_manifest') or manifest.get('source_manifest_hash') or '',
        'source_kind': source_kind,
        'source_label': source_label,
        'authorization_ref': authorization_ref,
        'checks': {
            'closed_books_pilot_entry_ready': manifest_closed_books_pilot_ready,
            'source_documentation_confirmed': effective_source_ready,
            'manifest_source_documentation_confirmed': manifest_source_ready,
            'ownership_evidence_confirmed': ownership_evidence_ready,
            'architecture_complete_for_mirror_run': effective_architecture_ready,
            'manifest_architecture_complete_for_mirror_run': manifest_architecture_ready,
            'comparison_closes_expected_output_value_equality': comparison_closes_value_equality_gap,
            'comparison_ready_for_mirror_conclusion': comparison_ready,
            'stage6_ready_for_renta_anual': stage6_ready,
            'mirror_run_evidence_confirmed': mirror_run_ready,
            'mirror_run_artifacts_linked': mirror_run_artifact_link_ready,
            'safety_boundary_ok': safety_ok,
        },
        'summary': {
            'ready_for_closed_books_pilot': ready_for_closed_books_pilot,
            'ready_for_architecture_proof': ready_for_architecture_proof,
            'ready_for_objective_completion': ready_for_objective_completion,
            'entry_classification': 'piloto_habilitado' if ready_for_closed_books_pilot else 'entrada_bloqueada',
            'classification': 'resuelto_confirmado' if ready_for_objective_completion else 'parcial',
            'blockers': sorted(set(blockers)),
        },
        'comparison_summary': comparison['summary'],
        'comparison_generated_artifact_evidence': comparison['generated_inventory'].get(
            'generated_artifact_evidence',
            {},
        ),
        'stage6_summary': {
            'classification': readiness['classification'],
            'ready_for_stage6_renta_anual': readiness['ready_for_stage6_renta_anual'],
            'issue_counts': readiness['issue_counts'],
            'issue_codes': [issue['code'] for issue in readiness['issues']],
        },
        'mirror_run_summary': mirror_run_summary,
        'mirror_run_artifact_link_summary': mirror_run_artifact_link_summary,
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'uses_expected_outputs_as_inputs': False,
            'expected_outputs_used_as_comparison_only': True,
            'final_tax_calculation': False,
        },
    }
