from __future__ import annotations

from pathlib import Path
from typing import Any

from core.annual_tax_expected_output_comparator import compare_annual_tax_expected_outputs
from core.stage6_renta_anual_readiness import collect_stage6_renta_anual_readiness


ANNUAL_TAX_MIRROR_PROOF_SCHEMA_VERSION = 'annual-tax-mirror-proof.v1'


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
    comparison_ready = bool(comparison['summary']['ready_for_mirror_conclusion'])
    stage6_ready = bool(readiness['ready_for_stage6_renta_anual'])
    safety_ok = _safety_ok(manifest=manifest, comparison=comparison)

    blockers = []
    if not manifest_source_ready:
        blockers.append('source_documentation_not_confirmed')
    if not manifest_architecture_ready:
        blockers.append('architecture_not_confirmed_for_mirror_run')
    if not comparison_ready:
        blockers.extend(f'comparison.{code}' for code in comparison['summary']['blockers'])
    if not stage6_ready:
        for issue in readiness['issues']:
            code = str(issue['code'])
            blockers.append(code if code.startswith('stage6.') else f'stage6.{code}')
    if not safety_ok:
        blockers.append('mirror_proof_safety_boundary_failed')

    ready_for_architecture_proof = comparison_ready and stage6_ready and safety_ok
    ready_for_objective_completion = (
        manifest_source_ready and manifest_architecture_ready and ready_for_architecture_proof
    )

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
            'source_documentation_confirmed': manifest_source_ready,
            'architecture_complete_for_mirror_run': manifest_architecture_ready,
            'comparison_ready_for_mirror_conclusion': comparison_ready,
            'stage6_ready_for_renta_anual': stage6_ready,
            'safety_boundary_ok': safety_ok,
        },
        'summary': {
            'ready_for_architecture_proof': ready_for_architecture_proof,
            'ready_for_objective_completion': ready_for_objective_completion,
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
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'uses_expected_outputs_as_inputs': False,
            'expected_outputs_used_as_comparison_only': True,
            'final_tax_calculation': False,
        },
    }
