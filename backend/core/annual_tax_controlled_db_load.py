from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from contabilidad.models import (
    BalanceComprobacion,
    CierreMensualContable,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    LibroDiario,
    LibroMayor,
    ObligacionTributariaMensual,
)
from core.annual_tax_controlled_load_plan import COMPARISON_ONLY_CATEGORIES
from core.annual_tax_source_manifest import payload_hash
from core.reference_validation import (
    contains_chilean_rut_reference,
    contains_local_absolute_path_reference,
    contains_sensitive_reference,
    is_non_sensitive_control_reference,
)
from patrimonio.models import EstadoPatrimonial, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble
from patrimonio.validators import validate_rut
from sii.models import (
    AnnualTaxOfficialSource,
    CapacidadSII,
    DestinoMapeoTributarioAnual,
    EstadoAnnualTaxOfficialSource,
    EstadoMonthlyTaxFact,
    F29PreparacionMensual,
    MonthlyTaxFact,
    TipoAnnualTaxOfficialSource,
)


CONTROLLED_DB_LOAD_SCHEMA_VERSION = 'annual-tax-controlled-db-load.v1'
CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION = 'annual-tax-ownership-review-handoff.v1'
SAFE_REF_PATTERN = re.compile(r'^[A-Za-z0-9_.:-]+$')

FORBIDDEN_EXPECTED_OUTPUT_KEYS = {
    'expected_outputs',
    'comparison_outputs_as_inputs',
    'annual_balance_expected_outputs',
    'annual_tax_register_expected_outputs',
    'ddjj_expected_outputs',
    'f22_expected_outputs',
    *COMPARISON_ONLY_CATEGORIES,
}

REFERENCE_FIELDS = (
    'company_ref',
    'source_manifest_hash',
    'responsible_ref',
    'approval_ref',
)


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or '').strip()
    if not value:
        raise ValueError(f'{key} es obligatorio.')
    if key != 'source_manifest_hash' and not is_non_sensitive_control_reference(value):
        raise ValueError(f'{key} debe ser una referencia no sensible.')
    return value


def _decimal(value: Any, *, field_name: str) -> Decimal:
    try:
        return Decimal(str(value if value is not None else '0.00'))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f'{field_name} debe ser decimal.') from error


def _date(value: Any, *, field_name: str, required: bool = True) -> date | None:
    if value in (None, '') and not required:
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise ValueError(f'{field_name} debe ser fecha ISO YYYY-MM-DD.') from error


def _validated_rut(value: Any, *, field_name: str) -> str:
    try:
        return validate_rut(str(value or '').strip())
    except ValidationError as error:
        raise ValueError(f'{field_name} debe ser un RUT valido.') from error


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_bool(value: Any) -> bool:
    return value is True


def _is_safe_ref(value: Any) -> bool:
    text = str(value or '').strip()
    return bool(text) and not (
        contains_sensitive_reference(text)
        or contains_chilean_rut_reference(text)
        or contains_local_absolute_path_reference(text)
        or not SAFE_REF_PATTERN.fullmatch(text)
    )


def _safe_summary_ref(value: Any, *, fallback: str) -> str:
    text = str(value or '').strip()
    return text if _is_safe_ref(text) else fallback


def _safe_ready_flags(raw_flags: Any) -> dict[str, bool]:
    if not isinstance(raw_flags, dict):
        return {}
    flags: dict[str, bool] = {}
    for raw_key, raw_value in raw_flags.items():
        key = str(raw_key or '').strip()
        if _is_safe_ref(key) and isinstance(raw_value, bool):
            flags[key] = raw_value
    return {key: flags[key] for key in sorted(flags)}


def _safe_source_issue_codes(raw_issue_codes: Any) -> list[dict[str, str]]:
    if not isinstance(raw_issue_codes, list):
        return []
    issue_codes: list[dict[str, str]] = []
    for raw_issue in raw_issue_codes:
        if not isinstance(raw_issue, dict):
            continue
        code = _safe_summary_ref(raw_issue.get('code'), fallback='redacted-issue-code')
        if not code:
            continue
        issue_codes.append(
            {
                'code': code,
                'severity': _safe_summary_ref(raw_issue.get('severity'), fallback='blocking'),
            }
        )
    return sorted(issue_codes, key=lambda item: (item['code'], item['severity']))


def _question_source_summaries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_summaries = payload.get('question_source_summaries')
    if not isinstance(raw_summaries, list):
        raw_summaries = payload.get('source_summaries')
    if not isinstance(raw_summaries, list):
        return []

    summaries: list[dict[str, Any]] = []
    for raw_summary in raw_summaries:
        if not isinstance(raw_summary, dict):
            continue
        summaries.append(
            {
                'label': _safe_summary_ref(raw_summary.get('label'), fallback='source'),
                'schema_version': _safe_summary_ref(
                    raw_summary.get('schema_version'),
                    fallback='schema-version-pending',
                ),
                'classification': _safe_summary_ref(
                    raw_summary.get('classification'),
                    fallback='classification-pending',
                ),
                'ready_flags': _safe_ready_flags(raw_summary.get('ready_flags')),
                'issues_total': _safe_int(raw_summary.get('issues_total')),
                'safe_issue_codes': _safe_source_issue_codes(raw_summary.get('safe_issue_codes')),
                'source_hash': _safe_summary_ref(raw_summary.get('source_hash'), fallback='source-hash-pending'),
            }
        )
    return sorted(summaries, key=lambda item: (item['label'], item['source_hash']))


def _ownership_review_handoff_summary(package: dict[str, Any]) -> dict[str, Any]:
    review = package.get('ownership_review')
    if not isinstance(review, dict):
        return {
            'present': False,
            'validation_present': False,
            'ready_for_controlled_db_load': False,
            'readiness_sources_total': 0,
            'question_source_summaries': [],
        }

    source_summaries = _question_source_summaries(review)
    return {
        'present': True,
        'schema_version': _safe_summary_ref(review.get('schema_version'), fallback='schema-version-pending'),
        'validation_present': _safe_bool(review.get('validation_present')),
        'redacted_patch_hash_present': bool(str(review.get('redacted_patch_hash') or '').strip()),
        'participants_count': _safe_int(review.get('participants_count')),
        'percentage_total': str(
            _decimal(review.get('percentage_total'), field_name='ownership_review.percentage_total')
        ),
        'blocking_items_total': _safe_int(review.get('blocking_items_total')),
        'ready_for_manual_review': _safe_bool(review.get('ready_for_manual_review')),
        'ready_for_controlled_db_load': _safe_bool(review.get('ready_for_controlled_db_load')),
        'can_inject_ownership_into_controlled_package': _safe_bool(
            review.get('can_inject_ownership_into_controlled_package')
        ),
        'readiness_sources_total': len(source_summaries),
        'question_source_summaries': source_summaries,
        'next_action': _safe_summary_ref(review.get('next_action'), fallback='next-action-pending'),
        'replaces_ownership_snapshot': False,
    }


def _forbidden_expected_output_paths(value: Any, path: str = '$') -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            item_path = f'{path}.{key_text}'
            if key_text in FORBIDDEN_EXPECTED_OUTPUT_KEYS:
                paths.append(item_path)
            if key_text == 'category' and str(item) in COMPARISON_ONLY_CATEGORIES:
                paths.append(item_path)
            paths.extend(_forbidden_expected_output_paths(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_forbidden_expected_output_paths(item, f'{path}[{index}]'))
    return paths


def _validate_ownership_snapshot(ownership: Any, *, commercial_year: int) -> None:
    if ownership in (None, {}):
        return
    if not isinstance(ownership, dict):
        raise ValueError('ownership debe ser un objeto JSON cuando se informa.')
    _required_text(ownership, 'source_ref')
    as_of = _date(ownership.get('as_of'), field_name='ownership.as_of')
    required_snapshot_date = date(commercial_year, 12, 31)
    if as_of != required_snapshot_date:
        raise ValueError('ownership.as_of debe ser el 31-12 del ano comercial del paquete.')
    participants = ownership.get('participants')
    if not isinstance(participants, list) or not participants:
        raise ValueError('ownership.participants debe contener socios vigentes.')

    period_start = date(commercial_year, 1, 1)
    period_end = date(commercial_year, 12, 31)
    total_percentage = Decimal('0.00')
    seen_ruts: set[str] = set()
    for index, participant in enumerate(participants):
        if not isinstance(participant, dict):
            raise ValueError(f'ownership.participants[{index}] debe ser un objeto JSON.')
        participant_type = str(participant.get('participant_type') or 'socio').strip().lower()
        if participant_type != 'socio':
            raise ValueError('ownership solo acepta participantes tipo socio para empresa_owner en el boundary actual.')
        _required_text(participant, 'participant_ref')
        _required_text(participant, 'evidence_ref')
        name = str(participant.get('name') or '').strip()
        if not name:
            raise ValueError(f'ownership.participants[{index}].name es obligatorio.')
        rut = _validated_rut(participant.get('rut'), field_name=f'ownership.participants[{index}].rut')
        if rut in seen_ruts:
            raise ValueError(f'ownership contiene RUT de socio duplicado: participants[{index}].rut.')
        seen_ruts.add(rut)
        percentage = _decimal(
            participant.get('percentage'),
            field_name=f'ownership.participants[{index}].percentage',
        )
        if percentage <= Decimal('0.00') or percentage > Decimal('100.00'):
            raise ValueError('ownership.participants[].percentage debe estar entre 0.01 y 100.00.')
        starts_on = _date(
            participant.get('vigente_desde') or period_start.isoformat(),
            field_name=f'ownership.participants[{index}].vigente_desde',
        )
        ends_on = _date(
            participant.get('vigente_hasta'),
            field_name=f'ownership.participants[{index}].vigente_hasta',
            required=False,
        )
        if ends_on and ends_on < starts_on:
            raise ValueError('ownership.participants[].vigente_hasta no puede ser anterior a vigente_desde.')
        if starts_on > period_end or (ends_on and ends_on < period_start):
            raise ValueError('ownership.participants[] debe solaparse con el ano comercial del paquete.')
        if starts_on > required_snapshot_date or (ends_on and ends_on < required_snapshot_date):
            raise ValueError('ownership.participants[] debe estar vigente al 31-12 del ano comercial del paquete.')
        total_percentage += percentage
    if total_percentage != Decimal('100.00'):
        raise ValueError('ownership.participants debe sumar 100.00%.')


def _validate_ownership_review_handoff_consistency(payload: dict[str, Any]) -> None:
    ownership = payload.get('ownership')
    review = payload.get('ownership_review')
    if not isinstance(ownership, dict) or not ownership or not isinstance(review, dict):
        return
    if not (review.get('ready_for_controlled_db_load') is True or review.get('validation_present') is True):
        return
    if review.get('schema_version') != CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION:
        raise ValueError(
            f'ownership_review.schema_version debe ser {CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION}.'
        )
    if not str(review.get('redacted_patch_hash') or '').strip():
        raise ValueError('ownership_review.redacted_patch_hash es obligatorio cuando package.ownership ya fue validado.')

    participants = ownership.get('participants') if isinstance(ownership.get('participants'), list) else []
    if int(review.get('participants_count') or 0) != len(participants):
        raise ValueError('ownership_review.participants_count no coincide con ownership.participants.')
    expected_percentage = sum(
        _decimal(participant.get('percentage'), field_name='ownership.participant.percentage')
        for participant in participants
        if isinstance(participant, dict)
    )
    review_percentage = _decimal(review.get('percentage_total'), field_name='ownership_review.percentage_total')
    if review_percentage != expected_percentage:
        raise ValueError('ownership_review.percentage_total no coincide con ownership.participants.')


def _real_estate_properties(real_estate: Any) -> list[dict[str, Any]]:
    if not isinstance(real_estate, dict):
        return []
    properties = real_estate.get('properties')
    return properties if isinstance(properties, list) else []


def _validate_real_estate_snapshot(real_estate: Any, *, commercial_year: int) -> None:
    if real_estate in (None, {}):
        return
    if not isinstance(real_estate, dict):
        raise ValueError('real_estate debe ser un objeto JSON cuando se informa.')
    _required_text(real_estate, 'source_ref')
    as_of = _date(real_estate.get('as_of'), field_name='real_estate.as_of')
    if as_of.year != commercial_year:
        raise ValueError('real_estate.as_of debe pertenecer al ano comercial del paquete.')
    properties = _real_estate_properties(real_estate)
    if not properties:
        raise ValueError('real_estate.properties debe contener propiedades revisadas.')

    seen_codes: set[str] = set()
    for index, item in enumerate(properties):
        if not isinstance(item, dict):
            raise ValueError(f'real_estate.properties[{index}] debe ser un objeto JSON.')
        for field_name in (
            'property_ref',
            'codigo_propiedad',
            'direccion',
            'comuna',
            'region',
            'tipo_inmueble',
            'evidence_ref',
            'contribuciones_evidence_ref',
        ):
            value = str(item.get(field_name) or '').strip()
            if not value:
                raise ValueError(f'real_estate.properties[{index}].{field_name} es obligatorio.')
            if field_name in {'property_ref', 'evidence_ref', 'contribuciones_evidence_ref'}:
                _required_text(item, field_name)
        code = str(item.get('codigo_propiedad') or '').strip()
        if len(code) > 16:
            raise ValueError('real_estate.properties[].codigo_propiedad no puede exceder 16 caracteres.')
        if code in seen_codes:
            raise ValueError('real_estate.properties contiene codigo_propiedad duplicado.')
        seen_codes.add(code)
        if str(item.get('tipo_inmueble') or '').strip() not in TipoInmueble.values:
            raise ValueError('real_estate.properties[].tipo_inmueble no es valido.')
        contribution = _decimal(
            item.get('contribuciones_clp'),
            field_name=f'real_estate.properties[{index}].contribuciones_clp',
        )
        if contribution < Decimal('0.00'):
            raise ValueError('real_estate.properties[].contribuciones_clp no puede ser negativo.')
        codigo_f22 = str(item.get('codigo_f22') or '').strip()
        if codigo_f22 and not is_non_sensitive_control_reference(codigo_f22):
            raise ValueError('real_estate.properties[].codigo_f22 debe ser una referencia no sensible.')


def _validate_labor_previsional_source(labor_previsional: Any) -> dict[str, Any]:
    if labor_previsional in (None, {}):
        return {'present': False, 'required': False, 'required_by_ddjj_forms': []}
    if not isinstance(labor_previsional, dict):
        raise ValueError('labor_previsional debe ser un objeto JSON cuando se informa.')

    required = labor_previsional.get('required') is True
    forms = [
        str(form or '').strip()
        for form in (labor_previsional.get('required_by_ddjj_forms') or [])
        if str(form or '').strip()
    ]
    source_ref = str(labor_previsional.get('source_ref') or '').strip()
    if required:
        if '1887' not in forms:
            raise ValueError('labor_previsional.required_by_ddjj_forms debe incluir 1887 cuando required=true.')
        if not source_ref:
            raise ValueError('labor_previsional.source_ref es obligatorio.')
        if not is_non_sensitive_control_reference(source_ref):
            raise ValueError('labor_previsional.source_ref debe ser una referencia no sensible.')
    elif source_ref and not is_non_sensitive_control_reference(source_ref):
        raise ValueError('labor_previsional.source_ref debe ser una referencia no sensible.')

    return {
        'present': True,
        'required': required,
        'required_by_ddjj_forms': forms,
        'source_ref': source_ref,
        'monthly_support_months': labor_previsional.get('monthly_support_months') or [],
        'final_tax_calculation': False,
    }


def _validate_package(payload: dict[str, Any]) -> tuple[int, int, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError('El paquete de carga debe ser un objeto JSON.')
    if payload.get('schema_version') != CONTROLLED_DB_LOAD_SCHEMA_VERSION:
        raise ValueError(f'schema_version debe ser {CONTROLLED_DB_LOAD_SCHEMA_VERSION}.')
    if payload.get('expected_outputs_used_as_inputs') is True:
        raise ValueError('El paquete no puede usar salidas esperadas como insumos.')
    forbidden_paths = _forbidden_expected_output_paths(payload)
    if forbidden_paths:
        raise ValueError(
            'El paquete no puede incluir salidas esperadas Balance/RLI/CPT/RAI/DDJJ/F22 finales como insumos: '
            + ', '.join(forbidden_paths[:5])
        )
    if contains_sensitive_reference(payload, include_sensitive_keys=True):
        raise ValueError('El paquete contiene referencias sensibles o claves no permitidas.')

    for field_name in REFERENCE_FIELDS:
        _required_text(payload, field_name)

    commercial_year = int(payload.get('commercial_year') or 0)
    tax_year = int(payload.get('tax_year') or 0)
    if commercial_year < 2000 or tax_year != commercial_year + 1:
        raise ValueError('commercial_year y tax_year deben formar un par AC/AT valido.')
    _validate_ownership_snapshot(payload.get('ownership'), commercial_year=commercial_year)
    _validate_ownership_review_handoff_consistency(payload)
    _validate_real_estate_snapshot(payload.get('real_estate'), commercial_year=commercial_year)
    _validate_labor_previsional_source(payload.get('labor_previsional'))

    months = payload.get('months')
    if not isinstance(months, list) or not months:
        raise ValueError('months debe contener al menos un mes normalizado.')
    seen = set()
    for item in months:
        if not isinstance(item, dict):
            raise ValueError('Cada mes debe ser un objeto JSON.')
        month = int(item.get('month') or 0)
        if month < 1 or month > 12:
            raise ValueError('month debe estar entre 1 y 12.')
        if month in seen:
            raise ValueError(f'Mes duplicado en paquete controlado: {month}.')
        seen.add(month)
        if not isinstance(item.get('ledger'), dict):
            raise ValueError(f'Mes {month} requiere ledger normalizado.')
        if not isinstance(item.get('balance'), dict):
            raise ValueError(f'Mes {month} requiere balance normalizado.')
        _required_text(item, 'source_ref')

    return (
        commercial_year,
        tax_year,
        _required_text(payload, 'source_manifest_hash'),
        _required_text(payload, 'responsible_ref'),
        _required_text(payload, 'approval_ref'),
    )


def _get_existing_or_new(model, **lookup):
    try:
        return model.objects.get(**lookup), False
    except model.DoesNotExist:
        return model(**lookup), True


def _mark_count(counts: dict[str, dict[str, int]], model_name: str, created: bool) -> None:
    bucket = counts.setdefault(model_name, {'created': 0, 'updated': 0})
    bucket['created' if created else 'updated'] += 1


def _save_validated(obj) -> None:
    try:
        obj.full_clean()
    except ValidationError as error:
        raise ValueError(error.message_dict if hasattr(error, 'message_dict') else error.messages) from error
    obj.save()


def _apply_ownership_snapshot(
    *,
    empresa,
    package: dict[str, Any],
    commercial_year: int,
    source_manifest_hash: str,
    responsible_ref: str,
    approval_ref: str,
    counts: dict[str, dict[str, int]],
) -> dict[str, Any]:
    ownership = package.get('ownership')
    if not isinstance(ownership, dict) or not ownership:
        return {'present': False, 'participants_loaded': 0}
    participants = ownership['participants']
    for participant in participants:
        rut = _validated_rut(participant.get('rut'), field_name='ownership.participant.rut')
        socio, created = _get_existing_or_new(Socio, rut=rut)
        socio.nombre = str(participant.get('name') or '').strip()
        socio.activo = True
        _save_validated(socio)
        _mark_count(counts, 'Socio', created)

        starts_on = _date(
            participant.get('vigente_desde') or f'{commercial_year}-01-01',
            field_name='ownership.participant.vigente_desde',
        )
        ends_on = _date(
            participant.get('vigente_hasta'),
            field_name='ownership.participant.vigente_hasta',
            required=False,
        )
        participation, created = _get_existing_or_new(
            ParticipacionPatrimonial,
            empresa_owner=empresa,
            participante_socio=socio,
            vigente_desde=starts_on,
            vigente_hasta=ends_on,
        )
        participation.porcentaje = _decimal(
            participant.get('percentage'),
            field_name='ownership.participant.percentage',
        )
        participation.activo = True
        _save_validated(participation)
        _mark_count(counts, 'ParticipacionPatrimonial', created)

    return {
        'present': True,
        'source_ref': ownership['source_ref'],
        'as_of': ownership['as_of'],
        'participants_loaded': len(participants),
        'source_manifest_hash': source_manifest_hash,
        'responsible_ref': responsible_ref,
        'approval_ref': approval_ref,
        'final_tax_calculation': False,
    }


def _apply_real_estate_snapshot(
    *,
    empresa,
    package: dict[str, Any],
    commercial_year: int,
    tax_year: int,
    source_manifest_hash: str,
    responsible_ref: str,
    approval_ref: str,
    counts: dict[str, dict[str, int]],
) -> dict[str, Any]:
    real_estate = package.get('real_estate')
    if not isinstance(real_estate, dict) or not real_estate:
        return {'present': False, 'properties_loaded': 0}

    values_by_property_id: dict[str, dict[str, Any]] = {}
    property_refs: list[str] = []
    for item in _real_estate_properties(real_estate):
        code = str(item.get('codigo_propiedad') or '').strip()
        property_obj, created = _get_existing_or_new(
            Propiedad,
            empresa_owner=empresa,
            codigo_propiedad=code,
        )
        property_obj.rol_avaluo = str(item.get('rol_avaluo') or '').strip()
        property_obj.direccion = str(item.get('direccion') or '').strip()
        property_obj.comuna = str(item.get('comuna') or '').strip()
        property_obj.region = str(item.get('region') or '').strip()
        property_obj.tipo_inmueble = str(item.get('tipo_inmueble') or '').strip()
        property_obj.estado = EstadoPatrimonial.ACTIVE
        _save_validated(property_obj)
        _mark_count(counts, 'Propiedad', created)

        contribution_value = _decimal(
            item.get('contribuciones_clp'),
            field_name='real_estate.property.contribuciones_clp',
        )
        values_by_property_id[str(property_obj.id)] = {
            'property_ref': str(item.get('property_ref') or '').strip(),
            'codigo_propiedad': property_obj.codigo_propiedad,
            'contribuciones_clp': str(contribution_value),
            'codigo_f22': str(item.get('codigo_f22') or '').strip(),
            'property_evidence_ref': str(item.get('evidence_ref') or '').strip(),
            'evidencia_ref': str(item.get('contribuciones_evidence_ref') or item.get('evidence_ref') or '').strip(),
            'final_tax_calculation': False,
        }
        property_refs.append(str(item.get('property_ref') or '').strip())

    config = empresa.configuracion_fiscal
    regime_code = config.regimen_tributario.codigo_regimen
    source_key = f'controlled-load-real-estate-contributions-at{tax_year}-{regime_code}'
    source, created = _get_existing_or_new(
        AnnualTaxOfficialSource,
        anio_tributario=tax_year,
        source_key=source_key,
    )
    source.source_type = TipoAnnualTaxOfficialSource.EXPERT_REVIEW
    source.title = f'Fuente controlada contribuciones bienes raices AT{tax_year}'
    source.source_ref = str(real_estate.get('source_ref') or '').strip()
    source.source_hash = payload_hash(
        {
            'source_key': source_key,
            'source_ref': source.source_ref,
            'source_manifest_hash': source_manifest_hash,
            'values_by_property_id': values_by_property_id,
        }
    )
    source.retrieved_on = timezone.localdate()
    source.responsible_ref = responsible_ref
    source.estado = EstadoAnnualTaxOfficialSource.APPROVED
    source.applies_to = DestinoMapeoTributarioAnual.F22
    source.regime_code = regime_code
    source.scope_note = (
        'Fuente local controlada para contribuciones de bienes raices AC/AT; '
        'no acredita consulta SII real ni calculo tributario final.'
    )
    source.metadata = {
        'source': 'annual_tax_controlled_db_load.real_estate',
        'real_estate_contributions': True,
        'values_by_property_id': values_by_property_id,
        'property_refs': property_refs,
        'approval_ref': approval_ref,
        'source_manifest_hash': source_manifest_hash,
        'final_tax_calculation': False,
    }
    _save_validated(source)
    _mark_count(counts, 'AnnualTaxOfficialSource', created)

    return {
        'present': True,
        'source_ref': real_estate['source_ref'],
        'as_of': real_estate['as_of'],
        'properties_loaded': len(values_by_property_id),
        'contribution_source_id': source.id,
        'source_manifest_hash': source_manifest_hash,
        'responsible_ref': responsible_ref,
        'approval_ref': approval_ref,
        'final_tax_calculation': False,
    }


def _snapshot_summary(
    *,
    package: dict[str, Any],
    month_payload: dict[str, Any],
    source_manifest_hash: str,
    responsible_ref: str,
) -> dict[str, Any]:
    ledger = month_payload['ledger']
    balance = month_payload['balance']
    obligations = month_payload.get('obligations') or []
    balance_summary = {
        'total_debe': str(_decimal(balance.get('total_debe'), field_name='balance.total_debe')),
        'total_haber': str(_decimal(balance.get('total_haber'), field_name='balance.total_haber')),
        'cuadrado': bool(balance.get('cuadrado')),
    }
    if isinstance(balance.get('lineas_balance_8_columnas'), list):
        balance_summary['lineas_balance_8_columnas'] = balance['lineas_balance_8_columnas']
        balance_summary['lineas_balance_8_columnas_source'] = str(
            balance.get('lineas_balance_8_columnas_source') or 'controlled_package'
        )
    if isinstance(balance.get('annual_inventory_totals'), dict):
        balance_summary['annual_inventory_totals'] = balance['annual_inventory_totals']
    if balance.get('annual_inventory_ref'):
        balance_summary['annual_inventory_ref'] = str(balance.get('annual_inventory_ref') or '').strip()

    return {
        'schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
        'company_ref': package['company_ref'],
        'source_manifest_hash': source_manifest_hash,
        'responsible_ref': responsible_ref,
        'source_ref': month_payload['source_ref'],
        'ledger': {
            'asientos_count': int(ledger.get('asientos_count') or 0),
            'cuentas_count': int(ledger.get('cuentas_count') or 0),
            'total_debe': str(_decimal(ledger.get('total_debe'), field_name='ledger.total_debe')),
            'total_haber': str(_decimal(ledger.get('total_haber'), field_name='ledger.total_haber')),
        },
        'balance': balance_summary,
        'obligations': [
            {
                'tipo': str(item.get('tipo') or item.get('obligacion_tipo') or '').strip(),
                'base_imponible': str(_decimal(item.get('base_imponible'), field_name='obligation.base_imponible')),
                'monto_calculado': str(_decimal(item.get('monto_calculado'), field_name='obligation.monto_calculado')),
            }
            for item in obligations
            if isinstance(item, dict)
        ],
        'f29': month_payload.get('f29') or {},
        'payroll': month_payload.get('payroll') or {},
        'expected_outputs_used_as_inputs': False,
        'final_tax_calculation': False,
    }


def _apply_month(
    *,
    empresa,
    package: dict[str, Any],
    month_payload: dict[str, Any],
    commercial_year: int,
    source_manifest_hash: str,
    responsible_ref: str,
    approval_ref: str,
    counts: dict[str, dict[str, int]],
) -> None:
    month = int(month_payload['month'])
    period = f'{commercial_year}-{month:02d}'
    now = timezone.now()
    summary = _snapshot_summary(
        package=package,
        month_payload=month_payload,
        source_manifest_hash=source_manifest_hash,
        responsible_ref=responsible_ref,
    )
    ledger = month_payload['ledger']
    balance = month_payload['balance']

    close, created = _get_existing_or_new(
        CierreMensualContable,
        empresa=empresa,
        anio=commercial_year,
        mes=month,
    )
    close.estado = EstadoCierreMensual.APPROVED
    close.fecha_preparacion = close.fecha_preparacion or now
    close.fecha_aprobacion = now
    close.resumen_obligaciones = {
        'controlled_load': True,
        'source_manifest_hash': source_manifest_hash,
        'source_ref': month_payload['source_ref'],
        'approval_ref': approval_ref,
        'obligations_count': len(month_payload.get('obligations') or []),
    }
    _save_validated(close)
    _mark_count(counts, 'CierreMensualContable', created)

    diario, created = _get_existing_or_new(LibroDiario, empresa=empresa, periodo=period)
    diario.estado_snapshot = EstadoCierreMensual.APPROVED
    diario.storage_ref = str(ledger.get('libro_diario_ref') or month_payload['source_ref']).strip()
    diario.resumen = summary['ledger'] | {
        'controlled_load': True,
        'source_manifest_hash': source_manifest_hash,
    }
    _save_validated(diario)
    _mark_count(counts, 'LibroDiario', created)

    mayor, created = _get_existing_or_new(LibroMayor, empresa=empresa, periodo=period)
    mayor.estado_snapshot = EstadoCierreMensual.APPROVED
    mayor.storage_ref = str(ledger.get('libro_mayor_ref') or month_payload['source_ref']).strip()
    mayor.resumen = summary['ledger'] | {
        'controlled_load': True,
        'source_manifest_hash': source_manifest_hash,
    }
    _save_validated(mayor)
    _mark_count(counts, 'LibroMayor', created)

    balance_obj, created = _get_existing_or_new(BalanceComprobacion, empresa=empresa, periodo=period)
    balance_obj.estado_snapshot = EstadoCierreMensual.APPROVED
    balance_obj.storage_ref = str(balance.get('balance_ref') or month_payload['source_ref']).strip()
    balance_obj.resumen = summary['balance'] | {
        'controlled_load': True,
        'source_manifest_hash': source_manifest_hash,
    }
    _save_validated(balance_obj)
    _mark_count(counts, 'BalanceComprobacion', created)

    for obligation_payload in month_payload.get('obligations') or []:
        if not isinstance(obligation_payload, dict):
            raise ValueError(f'Mes {month} contiene obligacion invalida.')
        obligation_type = str(
            obligation_payload.get('tipo') or obligation_payload.get('obligacion_tipo') or ''
        ).strip()
        if not obligation_type:
            raise ValueError(f'Mes {month} contiene obligacion sin tipo.')
        obligation, created = _get_existing_or_new(
            ObligacionTributariaMensual,
            empresa=empresa,
            anio=commercial_year,
            mes=month,
            obligacion_tipo=obligation_type,
        )
        obligation.base_imponible = _decimal(
            obligation_payload.get('base_imponible'),
            field_name='obligation.base_imponible',
        )
        obligation.monto_calculado = _decimal(
            obligation_payload.get('monto_calculado'),
            field_name='obligation.monto_calculado',
        )
        obligation.estado_preparacion = obligation_payload.get(
            'estado_preparacion',
            EstadoPreparacionTributaria.PREPARED,
        )
        obligation.detalle_calculo = {
            'controlled_load': True,
            'source_ref': obligation_payload.get('source_ref') or month_payload['source_ref'],
            'source_manifest_hash': source_manifest_hash,
        }
        _save_validated(obligation)
        _mark_count(counts, 'ObligacionTributariaMensual', created)

    f29_obj = None
    f29_payload = month_payload.get('f29')
    f29_no_declaration = (
        isinstance(f29_payload, dict)
        and f29_payload.get('estado_preparacion') == EstadoPreparacionTributaria.NOT_APPLICABLE
        and isinstance(f29_payload.get('resumen'), dict)
        and f29_payload['resumen'].get('no_declaration') is True
    )
    if isinstance(f29_payload, dict) and f29_payload and not f29_no_declaration:
        capability = empresa.capacidades_sii.filter(capacidad_key=CapacidadSII.F29_PREPARACION).first()
        if capability is None:
            raise ValueError(f'Mes {month} requiere CapacidadTributariaSII F29_PREPARACION para cargar F29.')
        f29_obj, created = _get_existing_or_new(
            F29PreparacionMensual,
            empresa=empresa,
            anio=commercial_year,
            mes=month,
        )
        f29_obj.capacidad_tributaria = capability
        f29_obj.cierre_mensual = close
        f29_obj.estado_preparacion = f29_payload.get(
            'estado_preparacion',
            EstadoPreparacionTributaria.PREPARED,
        )
        f29_obj.resumen_formulario = {
            'controlled_load': True,
            'source_manifest_hash': source_manifest_hash,
            **(f29_payload.get('resumen') if isinstance(f29_payload.get('resumen'), dict) else {}),
        }
        f29_obj.borrador_ref = str(f29_payload.get('borrador_ref') or '').strip()
        f29_obj.responsable_revision_ref = str(f29_payload.get('responsable_revision_ref') or responsible_ref).strip()
        f29_obj.observaciones = str(f29_payload.get('observaciones') or '').strip()
        _save_validated(f29_obj)
        _mark_count(counts, 'F29PreparacionMensual', created)

    fact, created = _get_existing_or_new(MonthlyTaxFact, empresa=empresa, anio=commercial_year, mes=month)
    fact.cierre_mensual = close
    fact.f29_preparacion = f29_obj
    fact.source_ref = month_payload['source_ref']
    fact.responsible_ref = responsible_ref
    fact.resumen_hecho = {
        'empresa_id': empresa.id,
        'anio': commercial_year,
        'mes': month,
        **summary,
    }
    fact.hash_hecho = payload_hash(fact.resumen_hecho)
    fact.estado = EstadoMonthlyTaxFact.NORMALIZED
    _save_validated(fact)
    _mark_count(counts, 'MonthlyTaxFact', created)


def apply_annual_tax_controlled_db_load(*, empresa, package: dict[str, Any], write_database: bool = False) -> dict[str, Any]:
    commercial_year, tax_year, source_manifest_hash, responsible_ref, approval_ref = _validate_package(package)
    months = sorted(int(item['month']) for item in package['months'])
    complete_12_months = months == list(range(1, 13))
    counts: dict[str, dict[str, int]] = {}

    if write_database:
        with transaction.atomic():
            ownership_summary = _apply_ownership_snapshot(
                empresa=empresa,
                package=package,
                commercial_year=commercial_year,
                source_manifest_hash=source_manifest_hash,
                responsible_ref=responsible_ref,
                approval_ref=approval_ref,
                counts=counts,
            )
            real_estate_summary = _apply_real_estate_snapshot(
                empresa=empresa,
                package=package,
                commercial_year=commercial_year,
                tax_year=tax_year,
                source_manifest_hash=source_manifest_hash,
                responsible_ref=responsible_ref,
                approval_ref=approval_ref,
                counts=counts,
            )
            for month_payload in sorted(package['months'], key=lambda item: int(item['month'])):
                _apply_month(
                    empresa=empresa,
                    package=package,
                    month_payload=month_payload,
                    commercial_year=commercial_year,
                    source_manifest_hash=source_manifest_hash,
                    responsible_ref=responsible_ref,
                    approval_ref=approval_ref,
                    counts=counts,
                )
    else:
        ownership_summary = {'present': bool(package.get('ownership')), 'participants_loaded': 0}
        real_estate_summary = {'present': bool(package.get('real_estate')), 'properties_loaded': 0}
    labor_previsional_summary = _validate_labor_previsional_source(package.get('labor_previsional'))

    blockers = []
    if not complete_12_months:
        blockers.append('controlled_package_incomplete_12_months')

    return {
        'schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
        'writes_database': write_database,
        'empresa_id': empresa.id,
        'company_ref': package['company_ref'],
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_manifest_hash': source_manifest_hash,
        'months_loaded': months if write_database else [],
        'months_validated': months,
        'complete_12_months': complete_12_months,
        'expected_outputs_used_as_inputs': False,
        'ownership_snapshot': ownership_summary,
        'ownership_review_handoff': _ownership_review_handoff_summary(package),
        'real_estate_snapshot': real_estate_summary,
        'labor_previsional_source': labor_previsional_summary,
        'created_updated': counts,
        'ready_for_annual_generation': write_database and complete_12_months and not blockers,
        'blockers': blockers,
        'safety': {
            'copies_source_files': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'uses_expected_outputs_as_inputs': False,
        },
    }
