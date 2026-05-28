from __future__ import annotations

import calendar
import re
import unicodedata
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.utils import timezone

from audit.models import AuditEvent
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from cobranza.models import (
    AjusteContrato,
    CANONICAL_UF_SOURCE_KEYS,
    DistribucionCobroMensual,
    GarantiaContractual,
    HistorialGarantia,
    PagoMensual,
    TipoMovimientoGarantia,
    ValorUFDiario,
)
from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoRegistro, RegimenTributarioEmpresa
from documentos.models import EstadoPoliticaFirma, TipoDocumental
from contratos.models import (
    Arrendatario,
    AvisoTermino,
    CodeudorSolidario,
    ContactoPagoArrendatario,
    Contrato,
    ContratoPropiedad,
    EstadoContactoArrendatario,
    EstadoContactoPago,
    EstadoAvisoTermino,
    EstadoCodeudorSolidario,
    EstadoContrato,
    MonedaBaseContrato,
    PeriodoContractual,
    RENEWAL_PERIOD_KIND,
    TENANT_REPLACEMENT_EVENT_TYPE,
    RolContratoPropiedad,
    TipoArrendatario,
    is_international_phone_number,
    normalize_representante_legal_snapshot,
)
from operacion.models import (
    AsignacionCanalOperacion,
    CuentaRecaudadora,
    EstadoAsignacionCanal,
    EstadoIdentidadEnvio,
    EstadoMandatoOperacion,
    IdentidadDeEnvio,
    MandatoOperacion,
)
from patrimonio.models import (
    ComunidadPatrimonial,
    Empresa,
    ModoRepresentacionComunidad,
    ParticipacionPatrimonial,
    Propiedad,
    RepresentacionComunidad,
    ServicioPropiedad,
    Socio,
    TipoServicioPropiedad,
)
from patrimonio.services import PARTICIPATION_TRANSFER_EVENT_TYPE
from patrimonio.validators import validate_rut


EVIDENCE_GRADE_SOURCE_KINDS = {'snapshot_controlado', 'real_autorizado'}
SENSITIVE_SOURCE_LABEL_RE = re.compile(
    r'://|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial|[0-9]{7,}-?[0-9kK]',
    re.IGNORECASE,
)
ACTIVE_CONTRACT_STATES = {EstadoContrato.ACTIVE, EstadoContrato.FUTURE}
REQUIRED_STAGE1_COUNTS = (
    'socios',
    'empresas',
    'comunidades',
    'participaciones_patrimoniales',
    'representaciones_comunidad',
    'propiedades',
    'cuentas_recaudadoras',
    'mandatos',
    'identidades_envio_activas',
    'asignaciones_canal_activas',
    'arrendatarios',
    'contratos',
    'contratos_activos_o_futuros',
    'contrato_propiedades',
    'periodos_contractuales',
    'garantias_contractuales',
    'mandatos_con_facturacion',
    'configuraciones_fiscales_activas',
)
AGGREGATE_DEFINITIONS = (
    {
        'key': 'socios',
        'canonical_entity': 'Socio',
        'entities': {'Socio'},
        'code_prefixes': ('stage1.socio.',),
    },
    {
        'key': 'empresas',
        'canonical_entity': 'Empresa',
        'entities': {'Empresa'},
        'code_prefixes': ('stage1.empresa.',),
    },
    {
        'key': 'comunidades',
        'canonical_entity': 'ComunidadPatrimonial',
        'entities': {'ComunidadPatrimonial'},
        'code_prefixes': ('stage1.comunidad.',),
    },
    {
        'key': 'participaciones_patrimoniales',
        'canonical_entity': 'ParticipacionPatrimonial',
        'entities': {'ParticipacionPatrimonial'},
        'code_prefixes': ('stage1.participacion.',),
    },
    {
        'key': 'representaciones_comunidad',
        'canonical_entity': 'RepresentacionComunidad',
        'entities': {'RepresentacionComunidad'},
        'code_prefixes': ('stage1.representacion.',),
    },
    {
        'key': 'propiedades',
        'canonical_entity': 'Propiedad',
        'entities': {'Propiedad', 'ServicioPropiedad'},
        'code_prefixes': ('stage1.propiedad.', 'stage1.servicio_propiedad.'),
    },
    {
        'key': 'cuentas_recaudadoras',
        'canonical_entity': 'CuentaRecaudadora',
        'entities': {'CuentaRecaudadora'},
        'code_prefixes': ('stage1.cuenta.',),
    },
    {
        'key': 'mandatos',
        'canonical_entity': 'MandatoOperacion',
        'entities': {'MandatoOperacion'},
        'code_prefixes': ('stage1.mandato.', 'stage1.facturacion.'),
    },
    {
        'key': 'identidades_envio_activas',
        'canonical_entity': 'IdentidadDeEnvio',
        'entities': {'IdentidadDeEnvio'},
        'code_prefixes': ('stage1.identidad_envio.',),
    },
    {
        'key': 'asignaciones_canal_activas',
        'canonical_entity': 'AsignacionCanalOperacion',
        'entities': {'AsignacionCanalOperacion'},
        'code_prefixes': ('stage1.asignacion_canal.', 'stage1.contrato.canal_operativo_'),
    },
    {
        'key': 'arrendatarios',
        'canonical_entity': 'Arrendatario',
        'entities': {'Arrendatario', 'ContactoPagoArrendatario'},
        'code_prefixes': ('stage1.arrendatario.', 'stage1.contacto_pago.'),
    },
    {
        'key': 'codeudores_solidarios',
        'canonical_entity': 'CodeudorSolidario',
        'entities': {'CodeudorSolidario'},
        'code_prefixes': ('stage1.codeudor.',),
    },
    {
        'key': 'contratos',
        'canonical_entity': 'Contrato',
        'entities': {'Contrato'},
        'code_prefixes': ('stage1.contrato.', 'stage1.contrato_futuro.', 'stage1.aviso_termino.'),
    },
    {
        'key': 'contratos_activos_o_futuros',
        'canonical_entity': 'Contrato',
        'entities': {'Contrato'},
        'code_prefixes': ('stage1.contrato.', 'stage1.contrato_futuro.', 'stage1.aviso_termino.'),
    },
    {
        'key': 'contrato_propiedades',
        'canonical_entity': 'ContratoPropiedad',
        'entities': {'ContratoPropiedad'},
        'code_prefixes': ('stage1.contrato_propiedad.', 'stage1.codigo_efectivo.'),
    },
    {
        'key': 'periodos_contractuales',
        'canonical_entity': 'PeriodoContractual',
        'entities': {'PeriodoContractual'},
        'code_prefixes': ('stage1.periodo.',),
    },
    {
        'key': 'ajustes_contrato',
        'canonical_entity': 'AjusteContrato',
        'entities': {'AjusteContrato'},
        'code_prefixes': ('stage1.ajuste_contrato.',),
    },
    {
        'key': 'pagos_mensuales',
        'canonical_entity': 'PagoMensual',
        'entities': {'PagoMensual'},
        'code_prefixes': ('stage1.pago_mensual.',),
    },
    {
        'key': 'distribuciones_cobro_mensual',
        'canonical_entity': 'DistribucionCobroMensual',
        'entities': {'DistribucionCobroMensual'},
        'code_prefixes': ('stage1.distribucion_cobro.',),
    },
    {
        'key': 'valores_uf_diarios',
        'canonical_entity': 'ValorUFDiario',
        'entities': {'ValorUFDiario'},
        'code_prefixes': ('stage1.valor_uf.', 'stage1.pago_mensual.uf_valor_'),
    },
    {
        'key': 'garantias_contractuales',
        'canonical_entity': 'GarantiaContractual',
        'entities': {'GarantiaContractual'},
        'code_prefixes': ('stage1.garantia.',),
    },
    {
        'key': 'historial_garantias',
        'canonical_entity': 'HistorialGarantia',
        'entities': {'HistorialGarantia'},
        'code_prefixes': ('stage1.historial_garantia.',),
    },
    {
        'key': 'mandatos_con_facturacion',
        'canonical_entity': 'MandatoOperacion',
        'entities': {'MandatoOperacion'},
        'code_prefixes': ('stage1.facturacion.',),
    },
    {
        'key': 'configuraciones_fiscales_activas',
        'canonical_entity': 'ConfiguracionFiscalEmpresa',
        'entities': {'ConfiguracionFiscalEmpresa', 'RegimenTributarioEmpresa'},
        'code_prefixes': (
            'stage1.configuracion_fiscal.',
            'stage1.regimen_tributario.',
            'stage1.facturacion.configuracion_',
        ),
    },
)


def _issue(
    issues: list[dict[str, Any]],
    *,
    code: str,
    entity: str,
    message: str,
    entity_id: int | None = None,
    severity: str = 'blocking',
) -> None:
    issues.append(
        {
            'code': code,
            'severity': severity,
            'entity': entity,
            'entity_id': entity_id,
            'message': message,
        }
    )


def _validation_messages(error: ValidationError) -> list[str]:
    if hasattr(error, 'message_dict'):
        messages: list[str] = []
        for field, field_messages in error.message_dict.items():
            for message in field_messages:
                messages.append(f'{field}: {message}')
        return messages
    return [str(message) for message in error.messages]


def _normalize_identity_text(value: str | None) -> str:
    normalized = unicodedata.normalize('NFKD', (value or '').strip())
    ascii_value = normalized.encode('ascii', 'ignore').decode('ascii')
    return ' '.join(ascii_value.upper().split())


def _normalize_rol_avaluo(value: str | None) -> str:
    return re.sub(r'[^0-9A-Z]', '', _normalize_identity_text(value))


def _property_identity(propiedad: Propiedad) -> str:
    return f'id={propiedad.pk}, codigo={propiedad.codigo_propiedad}, owner={propiedad.owner_tipo}:{propiedad.owner_id}'


def _date_windows_overlap(
    first_start: date,
    first_end: date | None,
    second_start: date,
    second_end: date | None,
) -> bool:
    if first_end is not None and second_start > first_end:
        return False
    if second_end is not None and first_start > second_end:
        return False
    return True


def _audit_model_validation(
    issues: list[dict[str, Any]],
    *,
    queryset: Any,
    code: str,
    entity: str,
) -> None:
    for instance in queryset:
        try:
            instance.full_clean()
        except ValidationError as error:
            for message in _validation_messages(error):
                _issue(
                    issues,
                    code=code,
                    entity=entity,
                    entity_id=instance.pk,
                    message=message,
                )


def _month_last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _month_first_day(year: int, month: int):
    return date(int(year), int(month), 1)


def _has_required_stage1_data(summary: dict[str, int]) -> bool:
    return all(summary[count_name] > 0 for count_name in REQUIRED_STAGE1_COUNTS)


def _source_label_looks_sensitive(source_label: str) -> bool:
    return bool(SENSITIVE_SOURCE_LABEL_RE.search(source_label))


def _safe_source_label(source_label: str) -> str:
    normalized = (source_label or '').strip()
    if _source_label_looks_sensitive(normalized):
        return '<redacted-invalid-source-label>'
    return normalized


def _safe_reference(value: str) -> str:
    normalized = (value or '').strip()
    if _source_label_looks_sensitive(normalized):
        return '<redacted-invalid-reference>'
    return normalized


def _audit_evidence_source_metadata(
    issues: list[dict[str, Any]],
    *,
    source_kind: str,
    source_label: str,
    authorization_ref: str,
    responsible_ref: str,
) -> None:
    if source_kind not in EVIDENCE_GRADE_SOURCE_KINDS:
        return

    if not source_label:
        _issue(
            issues,
            code='stage1.source_label.faltante',
            entity='Stage1Matrix',
            message='Una fuente evidencial requiere SourceLabel no sensible para trazabilidad.',
        )
        return

    if len(source_label) < 3 or _source_label_looks_sensitive(source_label):
        _issue(
            issues,
            code='stage1.source_label.sensible',
            entity='Stage1Matrix',
            message='SourceLabel de fuente evidencial parece vacio, demasiado corto o sensible; usar etiqueta trazable no secreta.',
        )

    if not authorization_ref:
        _issue(
            issues,
            code='stage1.authorization_ref.faltante',
            entity='Stage1Matrix',
            message='Una fuente evidencial requiere AuthorizationRef no sensible para probar autorizacion de uso.',
        )
    elif len(authorization_ref) < 3 or _source_label_looks_sensitive(authorization_ref):
        _issue(
            issues,
            code='stage1.authorization_ref.sensible',
            entity='Stage1Matrix',
            message='AuthorizationRef de fuente evidencial parece vacio, demasiado corto o sensible; usar referencia trazable no secreta.',
        )

    if not responsible_ref:
        _issue(
            issues,
            code='stage1.responsible_ref.faltante',
            entity='Stage1Matrix',
            message='Una fuente evidencial requiere ResponsibleRef no sensible para trazabilidad operacional.',
        )
    elif len(responsible_ref) < 3 or _source_label_looks_sensitive(responsible_ref):
        _issue(
            issues,
            code='stage1.responsible_ref.sensible',
            entity='Stage1Matrix',
            message='ResponsibleRef de fuente evidencial parece vacio, demasiado corto o sensible; usar referencia trazable no secreta.',
        )


def _issue_entity_id(issue: dict[str, Any]) -> int | None:
    entity_id = issue.get('entity_id')
    if entity_id is None:
        return None
    try:
        return int(entity_id)
    except (TypeError, ValueError):
        return None


def _issue_matches_active_or_future_contract(issue: dict[str, Any]) -> bool:
    entity_id = _issue_entity_id(issue)
    if entity_id is None:
        return False

    if issue.get('entity') == 'Contrato':
        return Contrato.objects.filter(pk=entity_id, estado__in=ACTIVE_CONTRACT_STATES).exists()

    if issue.get('entity') == 'AvisoTermino':
        return AvisoTermino.objects.filter(
            pk=entity_id,
            contrato__estado__in=ACTIVE_CONTRACT_STATES,
        ).exists()

    return False


def _issue_matches_aggregate(issue: dict[str, Any], definition: dict[str, Any]) -> bool:
    if definition['key'] == 'contratos_activos_o_futuros':
        return _issue_matches_active_or_future_contract(issue)

    if issue.get('entity') in definition['entities']:
        return True
    issue_code = issue.get('code') or ''
    return any(issue_code.startswith(prefix) for prefix in definition['code_prefixes'])


def _build_aggregate_classification(
    *,
    summary: dict[str, int],
    issues: list[dict[str, Any]],
    has_required_data: bool,
    evidence_grade: bool,
    require_data: bool,
) -> dict[str, dict[str, Any]]:
    aggregate_classification = {}
    for definition in AGGREGATE_DEFINITIONS:
        key = definition['key']
        blocking_codes = sorted(
            {
                issue['code']
                for issue in issues
                if issue.get('severity') == 'blocking'
                and issue.get('code') != 'stage1.data_missing'
                and _issue_matches_aggregate(issue, definition)
            }
        )
        count = summary[key]
        required = key in REQUIRED_STAGE1_COUNTS

        if blocking_codes:
            classification = 'defectuoso'
        elif required and count == 0:
            classification = 'bloqueado_dato_real' if require_data else 'implementado_sin_evidencia'
        elif evidence_grade and (count > 0 or has_required_data):
            classification = 'resuelto_confirmado'
        else:
            classification = 'implementado_sin_evidencia'

        aggregate_classification[key] = {
            'canonical_entity': definition['canonical_entity'],
            'count': count,
            'required_for_stage1_close': required,
            'classification': classification,
            'blocking_issue_codes': blocking_codes,
        }
    return aggregate_classification


def _audit_property_identity_uniqueness(issues: list[dict[str, Any]], active_properties: list[Propiedad]) -> None:
    by_rol: dict[str, list[Propiedad]] = defaultdict(list)
    by_operational_identity: dict[tuple[str, str, str, str, str], list[Propiedad]] = defaultdict(list)

    for propiedad in active_properties:
        rol_key = _normalize_rol_avaluo(propiedad.rol_avaluo)
        if rol_key:
            by_rol[rol_key].append(propiedad)

        identity_key = (
            _normalize_identity_text(propiedad.direccion),
            _normalize_identity_text(propiedad.comuna),
            _normalize_identity_text(propiedad.region),
            _normalize_identity_text(propiedad.tipo_inmueble),
            _normalize_identity_text(propiedad.codigo_propiedad),
        )
        if all(identity_key):
            by_operational_identity[identity_key].append(propiedad)

    for duplicate_properties in by_rol.values():
        if len(duplicate_properties) <= 1:
            continue
        duplicate_summary = ', '.join(_property_identity(propiedad) for propiedad in duplicate_properties)
        for propiedad in duplicate_properties:
            _issue(
                issues,
                code='stage1.propiedad.rol_avaluo_duplicado',
                entity='Propiedad',
                entity_id=propiedad.pk,
                message=(
                    'Propiedad activa comparte rol de avaluo normalizado con otro maestro activo; '
                    f'debe existir un solo maestro por propiedad real: {duplicate_summary}.'
                ),
            )

    for duplicate_properties in by_operational_identity.values():
        if len(duplicate_properties) <= 1:
            continue
        duplicate_summary = ', '.join(_property_identity(propiedad) for propiedad in duplicate_properties)
        for propiedad in duplicate_properties:
            _issue(
                issues,
                code='stage1.propiedad.identidad_operativa_duplicada',
                entity='Propiedad',
                entity_id=propiedad.pk,
                message=(
                    'Propiedad activa comparte direccion, comuna, region, tipo y codigo operativo con otro '
                    f'maestro activo; debe normalizarse sin duplicar propiedades: {duplicate_summary}.'
                ),
            )


def _audit_community_representation_window_overlaps(issues: list[dict[str, Any]]) -> None:
    representations_by_community: dict[int, list[RepresentacionComunidad]] = defaultdict(list)
    reported_communities: set[int] = set()
    representations = RepresentacionComunidad.objects.filter(activo=True).order_by(
        'comunidad_id',
        'vigente_desde',
        'id',
    )
    for representation in representations:
        community_representations = representations_by_community[representation.comunidad_id]
        if representation.comunidad_id not in reported_communities:
            for previous in community_representations:
                if _date_windows_overlap(
                    previous.vigente_desde,
                    previous.vigente_hasta,
                    representation.vigente_desde,
                    representation.vigente_hasta,
                ):
                    _issue(
                        issues,
                        code='stage1.comunidad.representacion_solapada',
                        entity='ComunidadPatrimonial',
                        entity_id=representation.comunidad_id,
                        message=(
                            'Comunidad con representaciones activas en ventanas efectivas solapadas; '
                            'debe existir solo una representacion vigente por fecha.'
                        ),
                    )
                    reported_communities.add(representation.comunidad_id)
                    break
        community_representations.append(representation)


def _audit_designated_community_representation_evidence(issues: list[dict[str, Any]]) -> None:
    representations = RepresentacionComunidad.objects.filter(
        activo=True,
        modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
    ).select_related('comunidad', 'socio_representante')
    for representation in representations:
        evidence_ref = (representation.evidencia_ref or '').strip()
        if not evidence_ref:
            _issue(
                issues,
                code='stage1.representacion.designada_evidencia_faltante',
                entity='RepresentacionComunidad',
                entity_id=representation.pk,
                message='Representacion designada activa sin evidencia formal trazable no sensible.',
            )
        elif not is_non_sensitive_reference(evidence_ref):
            _issue(
                issues,
                code='stage1.representacion.designada_evidencia_sensible',
                entity='RepresentacionComunidad',
                entity_id=representation.pk,
                message='Representacion designada activa con evidencia que parece sensible; registrar solo una referencia no secreta.',
            )


def _audit_community_representation_observations(issues: list[dict[str, Any]]) -> None:
    representations = RepresentacionComunidad.objects.filter(activo=True)
    for representation in representations:
        if contains_sensitive_reference(representation.observaciones, include_sensitive_keys=True):
            _issue(
                issues,
                code='stage1.representacion.observaciones_sensibles',
                entity='RepresentacionComunidad',
                entity_id=representation.pk,
                message=(
                    'Representacion de comunidad activa con observaciones que parecen contener referencias sensibles; '
                    'mover el detalle a evidencia segura y conservar solo una referencia no secreta.'
                ),
            )


def _metadata_str(value: Any) -> str:
    return '' if value is None else str(value).strip()


def _metadata_id_matches(value: Any, expected: int | None) -> bool:
    return bool(expected is not None and _metadata_str(value) == str(expected))


def _metadata_decimal_matches(value: Any, expected: Decimal) -> bool:
    try:
        return Decimal(str(value)) == expected
    except Exception:
        return False


def _metadata_ids_match(values: Any, expected_ids: set[int]) -> bool:
    if not isinstance(values, list):
        return False
    return {str(value) for value in values} == {str(value) for value in expected_ids}


def _participation_transfer_event_is_aligned(
    event: AuditEvent,
    *,
    participation: ParticipacionPatrimonial,
    successors: list[ParticipacionPatrimonial],
    effective_date: date,
) -> bool:
    metadata = event.metadata if isinstance(event.metadata, dict) else {}
    owner_tipo = 'empresa' if participation.empresa_owner_id else 'comunidad'
    owner_id = participation.empresa_owner_id or participation.comunidad_owner_id
    successor_ids = {item.pk for item in successors}
    transferred_percentage = sum((item.porcentaje for item in successors), Decimal('0.00'))
    reason = _metadata_str(metadata.get('reason'))
    evidence_ref = _metadata_str(metadata.get('evidence_ref'))

    return all(
        (
            event.actor_user_id is not None,
            event.entity_type == 'participacion_patrimonial',
            event.entity_id == str(participation.pk),
            metadata.get('owner_tipo') == owner_tipo,
            _metadata_id_matches(metadata.get('owner_id'), owner_id),
            _metadata_id_matches(metadata.get('origin_participation_id'), participation.pk),
            metadata.get('origin_participant_type') == participation.participante_tipo,
            _metadata_id_matches(metadata.get('origin_participant_id'), participation.participante_id),
            metadata.get('effective_date') == effective_date.isoformat(),
            bool(reason) and not contains_sensitive_reference(reason),
            bool(evidence_ref) and is_non_sensitive_reference(evidence_ref),
            _metadata_ids_match(metadata.get('target_participation_ids'), successor_ids),
            _metadata_id_matches(metadata.get('target_count'), len(successors)),
            _metadata_decimal_matches(metadata.get('transferred_percentage'), transferred_percentage),
        )
    )


def _participation_transfer_event_has_sensitive_reason(event: AuditEvent) -> bool:
    metadata = event.metadata if isinstance(event.metadata, dict) else {}
    reason = _metadata_str(metadata.get('reason'))
    return bool(reason) and contains_sensitive_reference(reason)


def _audit_participation_transfers(issues: list[dict[str, Any]]) -> None:
    ended_participations = ParticipacionPatrimonial.objects.filter(
        activo=True,
        vigente_hasta__isnull=False,
    ).select_related(
        'participante_socio',
        'participante_empresa',
        'empresa_owner',
        'comunidad_owner',
    )
    for participation in ended_participations:
        next_effective_date = participation.vigente_hasta + timedelta(days=1)
        successor_filter = {
            'activo': True,
            'vigente_desde': next_effective_date,
        }
        if participation.empresa_owner_id:
            successor_filter['empresa_owner_id'] = participation.empresa_owner_id
        else:
            successor_filter['comunidad_owner_id'] = participation.comunidad_owner_id
        successors = list(
            ParticipacionPatrimonial.objects.filter(**successor_filter).exclude(pk=participation.pk).order_by('id')
        )
        if not successors:
            continue
        audit_events = list(
            AuditEvent.objects.filter(event_type=PARTICIPATION_TRANSFER_EVENT_TYPE)
            .filter(
                Q(entity_id=str(participation.pk))
                | Q(metadata__origin_participation_id=participation.pk)
                | Q(metadata__origin_participation_id=str(participation.pk))
            )
            .order_by('-created_at')
        )
        if not audit_events:
            _issue(
                issues,
                code='stage1.participacion.transferencia_sin_auditoria',
                entity='ParticipacionPatrimonial',
                entity_id=participation.pk,
                message=(
                    'Participacion patrimonial terminada con sucesor inmediato sin evento auditado de '
                    'transferencia/reemplazo; debe usar el flujo guiado para conservar trazabilidad.'
                ),
            )
            continue
        if any(_participation_transfer_event_has_sensitive_reason(event) for event in audit_events):
            _issue(
                issues,
                code='stage1.participacion.transferencia_motivo_sensible',
                entity='ParticipacionPatrimonial',
                entity_id=participation.pk,
                message=(
                    'Participacion patrimonial terminada con evento de transferencia cuyo motivo contiene '
                    'referencias sensibles; la auditoria debe conservar solo motivo no sensible.'
                ),
            )
            continue
        if not any(
            _participation_transfer_event_is_aligned(
                event,
                participation=participation,
                successors=successors,
                effective_date=next_effective_date,
            )
            for event in audit_events
        ):
            _issue(
                issues,
                code='stage1.participacion.transferencia_auditoria_desalineada',
                entity='ParticipacionPatrimonial',
                entity_id=participation.pk,
                message=(
                    'Participacion patrimonial terminada con evento de transferencia incompleto o desalineado; '
                    'la auditoria debe conservar actor, owner, fecha efectiva, destinos, porcentaje, motivo y evidencia no sensible.'
                ),
            )


def _audit_mandate_window_overlaps(issues: list[dict[str, Any]]) -> None:
    mandates_by_property: dict[int, list[MandatoOperacion]] = defaultdict(list)
    reported_properties: set[int] = set()
    mandates = MandatoOperacion.objects.filter(estado=EstadoMandatoOperacion.ACTIVE).order_by(
        'propiedad_id',
        'vigencia_desde',
        'id',
    )
    for mandato in mandates:
        property_mandates = mandates_by_property[mandato.propiedad_id]
        if mandato.propiedad_id not in reported_properties:
            for previous in property_mandates:
                if _date_windows_overlap(
                    previous.vigencia_desde,
                    previous.vigencia_hasta,
                    mandato.vigencia_desde,
                    mandato.vigencia_hasta,
                ):
                    _issue(
                        issues,
                        code='stage1.mandato.ventana_solapada',
                        entity='MandatoOperacion',
                        entity_id=mandato.pk,
                        message=(
                            'Propiedad con mandatos operativos activos en ventanas efectivas solapadas; '
                            'debe existir solo un mandato vigente por fecha.'
                        ),
                    )
                    reported_properties.add(mandato.propiedad_id)
                    break
        property_mandates.append(mandato)


def _build_summary() -> dict[str, int]:
    socios_count = Socio.objects.count()
    empresas_count = Empresa.objects.count()
    comunidades_count = ComunidadPatrimonial.objects.count()
    return {
        'socios': socios_count,
        'empresas': empresas_count,
        'comunidades': comunidades_count,
        'owner_entities': socios_count + empresas_count + comunidades_count,
        'participaciones_patrimoniales': ParticipacionPatrimonial.objects.count(),
        'representaciones_comunidad': RepresentacionComunidad.objects.count(),
        'propiedades': Propiedad.objects.count(),
        'servicios_propiedad': ServicioPropiedad.objects.count(),
        'servicios_propiedad_activos': ServicioPropiedad.objects.filter(activo=True).count(),
        'cuentas_recaudadoras': CuentaRecaudadora.objects.count(),
        'mandatos': MandatoOperacion.objects.count(),
        'identidades_envio_activas': IdentidadDeEnvio.objects.filter(estado=EstadoIdentidadEnvio.ACTIVE).count(),
        'asignaciones_canal_activas': AsignacionCanalOperacion.objects.filter(
            estado=EstadoAsignacionCanal.ACTIVE
        ).count(),
        'arrendatarios': Arrendatario.objects.count(),
        'contactos_pago_arrendatario': ContactoPagoArrendatario.objects.count(),
        'contactos_pago_activos': ContactoPagoArrendatario.objects.filter(
            estado=EstadoContactoPago.ACTIVE,
        ).count(),
        'codeudores_solidarios': CodeudorSolidario.objects.count(),
        'codeudores_solidarios_activos': CodeudorSolidario.objects.filter(
            estado=EstadoCodeudorSolidario.ACTIVE
        ).count(),
        'contratos': Contrato.objects.count(),
        'contratos_activos_o_futuros': Contrato.objects.filter(estado__in=ACTIVE_CONTRACT_STATES).count(),
        'contrato_propiedades': ContratoPropiedad.objects.count(),
        'periodos_contractuales': PeriodoContractual.objects.count(),
        'ajustes_contrato': AjusteContrato.objects.count(),
        'pagos_mensuales': PagoMensual.objects.count(),
        'distribuciones_cobro_mensual': DistribucionCobroMensual.objects.count(),
        'valores_uf_diarios': ValorUFDiario.objects.count(),
        'garantias_contractuales': GarantiaContractual.objects.count(),
        'historial_garantias': HistorialGarantia.objects.count(),
        'mandatos_con_facturacion': MandatoOperacion.objects.filter(autoriza_facturacion=True).count(),
        'configuraciones_fiscales_activas': ConfiguracionFiscalEmpresa.objects.filter(
            estado=EstadoRegistro.ACTIVE
        ).count(),
    }


def _audit_patrimonio(issues: list[dict[str, Any]]) -> None:
    _audit_model_validation(
        issues,
        queryset=Socio.objects.all(),
        code='stage1.socio.validacion_modelo',
        entity='Socio',
    )
    _audit_model_validation(
        issues,
        queryset=Empresa.objects.all(),
        code='stage1.empresa.validacion_modelo',
        entity='Empresa',
    )
    _audit_model_validation(
        issues,
        queryset=ComunidadPatrimonial.objects.all(),
        code='stage1.comunidad.validacion_modelo',
        entity='ComunidadPatrimonial',
    )
    _audit_model_validation(
        issues,
        queryset=ParticipacionPatrimonial.objects.select_related(
            'participante_socio',
            'participante_empresa',
            'empresa_owner',
            'comunidad_owner',
        ),
        code='stage1.participacion.validacion_modelo',
        entity='ParticipacionPatrimonial',
    )
    _audit_model_validation(
        issues,
        queryset=RepresentacionComunidad.objects.select_related('comunidad', 'socio_representante'),
        code='stage1.representacion.validacion_modelo',
        entity='RepresentacionComunidad',
    )
    _audit_model_validation(
        issues,
        queryset=Propiedad.objects.select_related('empresa_owner', 'comunidad_owner', 'socio_owner'),
        code='stage1.propiedad.validacion_modelo',
        entity='Propiedad',
    )
    _audit_model_validation(
        issues,
        queryset=ServicioPropiedad.objects.select_related('propiedad'),
        code='stage1.servicio_propiedad.validacion_modelo',
        entity='ServicioPropiedad',
    )
    _audit_community_representation_window_overlaps(issues)
    _audit_designated_community_representation_evidence(issues)
    _audit_community_representation_observations(issues)
    _audit_participation_transfers(issues)

    for empresa in Empresa.objects.filter(estado='activa'):
        total = empresa.total_participaciones_activas()
        if total != Decimal('100.00'):
            _issue(
                issues,
                code='stage1.empresa.participaciones_incompletas',
                entity='Empresa',
                entity_id=empresa.pk,
                message=f'Empresa activa con participaciones vigentes sumando {total}, debe sumar 100.00.',
            )

    for comunidad in ComunidadPatrimonial.objects.filter(estado='activa'):
        total = comunidad.total_participaciones_activas()
        if total != Decimal('100.00'):
            _issue(
                issues,
                code='stage1.comunidad.participaciones_incompletas',
                entity='ComunidadPatrimonial',
                entity_id=comunidad.pk,
                message=f'Comunidad activa con participaciones vigentes sumando {total}, debe sumar 100.00.',
            )
        representation_count = comunidad.representaciones_activas().count()
        if representation_count != 1:
            _issue(
                issues,
                code='stage1.comunidad.representacion_activa_invalida',
                entity='ComunidadPatrimonial',
                entity_id=comunidad.pk,
                message=f'Comunidad activa con {representation_count} representaciones vigentes; debe tener exactamente una.',
            )

    active_properties = Propiedad.objects.filter(estado='activa').select_related(
        'empresa_owner',
        'comunidad_owner',
        'socio_owner',
    )
    active_properties = list(active_properties)
    _audit_property_identity_uniqueness(issues, active_properties)

    for propiedad in active_properties:
        current_date = timezone.localdate()
        current_mandates_count = propiedad.mandatos_operacion.filter(
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde__lte=current_date,
        ).filter(
            Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=current_date),
        ).count()
        if current_mandates_count != 1:
            _issue(
                issues,
                code='stage1.propiedad.mandato_activo_invalido',
                entity='Propiedad',
                entity_id=propiedad.pk,
                message=f'Propiedad activa con {current_mandates_count} mandatos vigentes; debe tener exactamente uno.',
            )


def _audit_operacion(issues: list[dict[str, Any]]) -> None:
    _audit_model_validation(
        issues,
        queryset=CuentaRecaudadora.objects.select_related('empresa_owner', 'comunidad_owner', 'socio_owner'),
        code='stage1.cuenta.validacion_modelo',
        entity='CuentaRecaudadora',
    )
    _audit_model_validation(
        issues,
        queryset=IdentidadDeEnvio.objects.select_related('empresa_owner', 'socio_owner'),
        code='stage1.identidad_envio.validacion_modelo',
        entity='IdentidadDeEnvio',
    )

    fiscal_config_by_company = set(
        ConfiguracionFiscalEmpresa.objects.filter(estado=EstadoRegistro.ACTIVE).values_list('empresa_id', flat=True)
    )
    for mandato in MandatoOperacion.objects.select_related(
        'propiedad',
        'cuenta_recaudadora',
        'entidad_facturadora',
        'propietario_empresa_owner',
        'propietario_comunidad_owner',
        'propietario_socio_owner',
        'administrador_empresa_owner',
        'administrador_socio_owner',
        'recaudador_empresa_owner',
        'recaudador_comunidad_owner',
        'recaudador_socio_owner',
    ):
        try:
            mandato.full_clean()
        except ValidationError as error:
            for message in _validation_messages(error):
                _issue(
                    issues,
                    code='stage1.mandato.validacion_modelo',
                    entity='MandatoOperacion',
                    entity_id=mandato.pk,
                    message=message,
                )
        if mandato.autoriza_facturacion:
            if not mandato.entidad_facturadora_id:
                _issue(
                    issues,
                    code='stage1.facturacion.entidad_faltante',
                    entity='MandatoOperacion',
                    entity_id=mandato.pk,
                    message='Mandato autoriza facturacion sin entidad facturadora.',
                )
            elif mandato.entidad_facturadora_id not in fiscal_config_by_company:
                _issue(
                    issues,
                    code='stage1.facturacion.configuracion_fiscal_faltante',
                    entity='MandatoOperacion',
                    entity_id=mandato.pk,
                    message='Entidad facturadora sin ConfiguracionFiscalEmpresa activa.',
                )

        if mandato.requires_operational_authority():
            if not mandato.autoridad_operativa_nombre.strip():
                _issue(
                    issues,
                    code='stage1.mandato.autoridad_operativa_nombre_faltante',
                    entity='MandatoOperacion',
                    entity_id=mandato.pk,
                    message='Mandato activo que comunica o factura documentos no tiene autoridad operativa vigente.',
                )

            if not mandato.autoridad_operativa_rut:
                _issue(
                    issues,
                    code='stage1.mandato.autoridad_operativa_rut_faltante',
                    entity='MandatoOperacion',
                    entity_id=mandato.pk,
                    message='Mandato activo que comunica o factura documentos no tiene RUT de autoridad operativa.',
                )
            else:
                try:
                    validate_rut(mandato.autoridad_operativa_rut)
                except ValidationError:
                    _issue(
                        issues,
                        code='stage1.mandato.autoridad_operativa_rut_invalido',
                        entity='MandatoOperacion',
                        entity_id=mandato.pk,
                        message='Mandato activo que comunica o factura documentos tiene RUT de autoridad operativa invalido.',
                    )

            if not mandato.autoridad_operativa_evidencia_ref.strip():
                _issue(
                    issues,
                    code='stage1.mandato.autoridad_operativa_evidencia_faltante',
                    entity='MandatoOperacion',
                    entity_id=mandato.pk,
                    message='Mandato activo que comunica o factura documentos no tiene evidencia trazable de autoridad.',
                )
            elif not is_non_sensitive_reference(mandato.autoridad_operativa_evidencia_ref):
                _issue(
                    issues,
                    code='stage1.mandato.autoridad_operativa_evidencia_sensible',
                    entity='MandatoOperacion',
                    entity_id=mandato.pk,
                    message='Mandato activo que comunica o factura documentos expone una evidencia sensible.',
                )

    _audit_mandate_window_overlaps(issues)

    _audit_model_validation(
        issues,
        queryset=AsignacionCanalOperacion.objects.select_related(
            'mandato_operacion',
            'mandato_operacion__propiedad',
            'mandato_operacion__entidad_facturadora',
            'mandato_operacion__administrador_empresa_owner',
            'mandato_operacion__administrador_socio_owner',
            'mandato_operacion__propietario_empresa_owner',
            'mandato_operacion__propietario_comunidad_owner',
            'mandato_operacion__propietario_socio_owner',
            'identidad_envio',
        ),
        code='stage1.asignacion_canal.validacion_modelo',
        entity='AsignacionCanalOperacion',
    )

    for asignacion in AsignacionCanalOperacion.objects.filter(
        estado=EstadoAsignacionCanal.ACTIVE,
    ).select_related(
        'mandato_operacion',
        'mandato_operacion__entidad_facturadora',
        'mandato_operacion__administrador_empresa_owner',
        'mandato_operacion__administrador_socio_owner',
        'mandato_operacion__propietario_empresa_owner',
        'mandato_operacion__propietario_comunidad_owner',
        'mandato_operacion__propietario_socio_owner',
        'identidad_envio',
    ):
        mandato = asignacion.mandato_operacion
        identity_owner = (asignacion.identidad_envio.owner_tipo, asignacion.identidad_envio.owner_id)
        admin_tuple = mandato.administrador_tuple()
        facturadora_tuple = mandato.facturadora_tuple()
        propietario_tuple = mandato.propietario_tuple()
        allowed_owners = {admin_tuple, facturadora_tuple}

        if identity_owner not in allowed_owners:
            _issue(
                issues,
                code='stage1.asignacion_canal.identidad_owner_no_autorizado',
                entity='AsignacionCanalOperacion',
                entity_id=asignacion.pk,
                message=(
                    'Asignacion activa usa una identidad de envio que no pertenece a la entidad facturadora '
                    'ni al administrador operativo del mandato.'
                ),
            )

        if identity_owner != propietario_tuple and not mandato.autoriza_comunicacion:
            _issue(
                issues,
                code='stage1.asignacion_canal.comunicacion_no_autorizada',
                entity='AsignacionCanalOperacion',
                entity_id=asignacion.pk,
                message=(
                    'Asignacion activa usa identidad de un actor distinto al propietario sin autorizacion '
                    'de comunicacion en el mandato.'
                ),
            )


def _audit_facturacion(issues: list[dict[str, Any]]) -> None:
    _audit_model_validation(
        issues,
        queryset=RegimenTributarioEmpresa.objects.all(),
        code='stage1.regimen_tributario.validacion_modelo',
        entity='RegimenTributarioEmpresa',
    )
    _audit_model_validation(
        issues,
        queryset=ConfiguracionFiscalEmpresa.objects.select_related('empresa', 'regimen_tributario'),
        code='stage1.configuracion_fiscal.validacion_modelo',
        entity='ConfiguracionFiscalEmpresa',
    )


def _audit_contract_periods(issues: list[dict[str, Any]], contrato: Contrato) -> None:
    periods = list(contrato.periodos_contractuales.order_by('fecha_inicio', 'numero_periodo'))
    if not periods:
        _issue(
            issues,
            code='stage1.contrato.periodos_faltantes',
            entity='Contrato',
            entity_id=contrato.pk,
            message='Contrato vigente o futuro sin periodos contractuales.',
        )
        return

    if periods[0].fecha_inicio != contrato.fecha_inicio:
        _issue(
            issues,
            code='stage1.contrato.periodos_no_cubren_inicio',
            entity='Contrato',
            entity_id=contrato.pk,
            message='El primer periodo contractual no coincide con la fecha de inicio del contrato.',
        )
    if periods[-1].fecha_fin != contrato.fecha_fin_vigente:
        _issue(
            issues,
            code='stage1.contrato.periodos_no_cubren_fin',
            entity='Contrato',
            entity_id=contrato.pk,
            message='El ultimo periodo contractual no coincide con la fecha fin vigente del contrato.',
        )

    for previous, current in zip(periods, periods[1:]):
        expected_start = previous.fecha_fin + timedelta(days=1)
        if current.fecha_inicio != expected_start:
            _issue(
                issues,
                code='stage1.contrato.periodos_discontinuos',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Los periodos contractuales tienen huecos o traslapes internos.',
            )
            break

    for period in periods:
        if period.moneda_base == MonedaBaseContrato.CLP and period.monto_base < Decimal('1000.00'):
            _issue(
                issues,
                code='stage1.periodo.monto_clp_bajo_minimo',
                entity='PeriodoContractual',
                entity_id=period.pk,
                message='Periodo CLP bajo el minimo operativo de 1.000.',
            )
        if period.moneda_base == MonedaBaseContrato.UF and period.monto_base <= Decimal('0.00'):
            _issue(
                issues,
                code='stage1.periodo.monto_uf_invalido',
                entity='PeriodoContractual',
                entity_id=period.pk,
                message='Periodo UF debe tener monto positivo y UF exacta disponible al calcular cobro.',
            )
        if period.is_automatic_renewal_origin() and not period.has_automatic_renewal_audit():
            _issue(
                issues,
                code='stage1.periodo.renovacion_automatica_sin_auditoria',
                entity='PeriodoContractual',
                entity_id=period.pk,
                message='Renovacion automatica sin evento auditable dedicado.',
            )

    if contrato.tiene_tramos:
        for previous, current in zip(periods, periods[1:]):
            base_changed = (
                current.moneda_base != previous.moneda_base
                or Decimal(current.monto_base) != Decimal(previous.monto_base)
            )
            if (
                str(current.tipo_periodo or '').strip().lower() == RENEWAL_PERIOD_KIND
                and base_changed
                and (
                    not current.has_renewal_base_policy()
                    or not is_non_sensitive_reference(current.politica_base_renovacion_ref)
                )
            ):
                _issue(
                    issues,
                    code='stage1.periodo.renovacion_base_sin_politica',
                    entity='PeriodoContractual',
                    entity_id=current.pk,
                    message=(
                        'Renovacion contractual con base distinta al ultimo tramo vigente '
                        'requiere politica documentada no sensible.'
                    ),
                )
            elif (
                str(current.tipo_periodo or '').strip().lower() == RENEWAL_PERIOD_KIND
                and base_changed
                and contains_sensitive_reference(current.politica_base_renovacion_motivo)
            ):
                _issue(
                    issues,
                    code='stage1.periodo.renovacion_base_politica_sensible',
                    entity='PeriodoContractual',
                    entity_id=current.pk,
                    message=(
                        'Renovacion contractual con base distinta al ultimo tramo vigente '
                        'contiene motivo de politica con referencias sensibles.'
                    ),
                )


def _audit_future_contract_closure_evidence(
    issues: list[dict[str, Any]],
    *,
    contrato: Contrato,
    primary_property_id: int | None,
) -> None:
    if contrato.estado != EstadoContrato.FUTURE or primary_property_id is None:
        return

    current_contract = (
        Contrato.objects.filter(
            estado=EstadoContrato.ACTIVE,
            contrato_propiedades__propiedad_id=primary_property_id,
            contrato_propiedades__rol_en_contrato=RolContratoPropiedad.PRIMARY,
        )
        .exclude(pk=contrato.pk)
        .order_by('-fecha_inicio', '-id')
        .first()
    )
    if current_contract:
        aviso = AvisoTermino.objects.filter(
            contrato=current_contract,
            estado=EstadoAvisoTermino.REGISTERED,
            fecha_efectiva__lte=contrato.fecha_inicio,
        ).order_by('-fecha_efectiva', '-id').first()
        if aviso is None:
            _issue(
                issues,
                code='stage1.contrato_futuro.aviso_termino_faltante',
                entity='Contrato',
                entity_id=contrato.pk,
                message=(
                    'Contrato futuro requiere AvisoTermino registrado para el contrato vigente '
                    'de la propiedad principal.'
                ),
            )
        elif (
            aviso.has_executed_renewal_conflict(contrato.fecha_inicio)
            and (
                not aviso.has_renewal_conflict_resolution()
                or not is_non_sensitive_reference(aviso.resolucion_conflicto_renovacion_ref)
            )
        ):
            _issue(
                issues,
                code='stage1.contrato_futuro.conflicto_renovacion_sin_resolucion',
                entity='Contrato',
                entity_id=contrato.pk,
                message=(
                    'Contrato futuro coexiste con AvisoTermino y renovacion ya ejecutada; '
                    'requiere resolucion guiada no sensible antes de considerarse integro.'
                ),
            )
        elif (
            aviso.has_executed_renewal_conflict(contrato.fecha_inicio)
            and contains_sensitive_reference(aviso.resolucion_conflicto_renovacion_motivo)
        ):
            _issue(
                issues,
                code='stage1.contrato_futuro.conflicto_renovacion_resolucion_sensible',
                entity='Contrato',
                entity_id=contrato.pk,
                message=(
                    'Contrato futuro coexiste con AvisoTermino y renovacion ya ejecutada; '
                    'la resolucion guiada contiene motivo sensible.'
                ),
            )
        elif contrato.arrendatario_id != current_contract.arrendatario_id and not AuditEvent.objects.filter(
            event_type=TENANT_REPLACEMENT_EVENT_TYPE,
            entity_type='contrato',
            entity_id=str(contrato.pk),
            metadata__contrato_anterior_id=current_contract.pk,
            metadata__aviso_termino_id=aviso.pk,
            metadata__arrendatario_anterior_id=current_contract.arrendatario_id,
            metadata__arrendatario_nuevo_id=contrato.arrendatario_id,
        ).exists():
            _issue(
                issues,
                code='stage1.contrato_futuro.cambio_arrendatario_sin_auditoria',
                entity='Contrato',
                entity_id=contrato.pk,
                message=(
                    'Contrato futuro con cambio de arrendatario requiere flujo guiado y evento auditable '
                    'que vincule contrato anterior, aviso de termino y contrato nuevo.'
                ),
            )
        return

    early_terminated_exists = (
        Contrato.objects.filter(
            estado=EstadoContrato.EARLY_TERMINATED,
            fecha_fin_vigente__lte=contrato.fecha_inicio,
            contrato_propiedades__propiedad_id=primary_property_id,
            contrato_propiedades__rol_en_contrato=RolContratoPropiedad.PRIMARY,
        )
        .exclude(pk=contrato.pk)
        .exists()
    )
    if not early_terminated_exists:
        _issue(
            issues,
            code='stage1.contrato_futuro.respaldo_cierre_faltante',
            entity='Contrato',
            entity_id=contrato.pk,
            message=(
                'Contrato futuro requiere AvisoTermino registrado o terminacion anticipada '
                'ejecutada sobre la propiedad principal.'
            ),
        )


def _audit_early_termination_proration(issues: list[dict[str, Any]]) -> None:
    contracts = Contrato.objects.filter(estado=EstadoContrato.EARLY_TERMINATED)
    for contrato in contracts:
        if not contrato.has_partial_early_termination_month():
            continue
        if not contrato.has_early_termination_proration_decision():
            _issue(
                issues,
                code='stage1.contrato.terminacion_anticipada_prorrata_sin_decision',
                entity='Contrato',
                entity_id=contrato.pk,
                message=(
                    'Contrato terminado anticipadamente con ultimo mes parcial requiere regla o decision '
                    'auditada con referencia no sensible y motivo trazable.'
                ),
            )
            continue
        if (
            not is_non_sensitive_reference(contrato.terminacion_anticipada_prorrata_ref)
            or contains_sensitive_reference(contrato.terminacion_anticipada_prorrata_motivo)
        ):
            _issue(
                issues,
                code='stage1.contrato.terminacion_anticipada_prorrata_sensible',
                entity='Contrato',
                entity_id=contrato.pk,
                message=(
                    'Contrato terminado anticipadamente con ultimo mes parcial conserva '
                    'decision de prorrata con referencia o motivo sensible.'
                ),
            )
            continue
        if not contrato.has_early_termination_proration_audit():
            _issue(
                issues,
                code='stage1.contrato.terminacion_anticipada_prorrata_sin_auditoria',
                entity='Contrato',
                entity_id=contrato.pk,
                message=(
                    'Contrato terminado anticipadamente con ultimo mes parcial conserva decision, '
                    'pero no tiene evento auditable dedicado para esa prorrata.'
                ),
            )


def _audit_late_termination_notices(issues: list[dict[str, Any]]) -> None:
    for aviso in AvisoTermino.objects.filter(estado=EstadoAvisoTermino.REGISTERED).select_related('contrato'):
        if not aviso.is_late_registered_notice():
            continue
        _issue(
            issues,
            code='stage1.aviso_termino.registro_fuera_plazo',
            entity='AvisoTermino',
            entity_id=aviso.pk,
            message=aviso.late_registration_alert(),
            severity='warning',
        )


def _audit_contract_tenant_readiness(issues: list[dict[str, Any]], contrato: Contrato) -> None:
    tenant = contrato.arrendatario
    if tenant.estado_contacto != EstadoContactoArrendatario.ACTIVE:
        _issue(
            issues,
            code='stage1.arrendatario.contacto_no_activo',
            entity='Arrendatario',
            entity_id=tenant.pk,
            message='Contrato vigente o futuro requiere arrendatario con estado de contacto activo.',
        )

    if not ((tenant.email or '').strip() or (tenant.telefono or '').strip()):
        _issue(
            issues,
            code='stage1.arrendatario.contacto_operativo_faltante',
            entity='Arrendatario',
            entity_id=tenant.pk,
            message='Contrato vigente o futuro requiere email o telefono operativo del arrendatario.',
        )

    if tenant.whatsapp_opt_in and not is_international_phone_number(tenant.telefono):
        _issue(
            issues,
            code='stage1.arrendatario.whatsapp_telefono_invalido',
            entity='Arrendatario',
            entity_id=tenant.pk,
            message='Arrendatario con WhatsApp operativo requiere telefono en formato internacional.',
        )

    if not (tenant.domicilio_notificaciones or '').strip():
        _issue(
            issues,
            code='stage1.arrendatario.domicilio_notificaciones_faltante',
            entity='Arrendatario',
            entity_id=tenant.pk,
            message='Contrato vigente o futuro requiere domicilio de notificaciones del arrendatario.',
        )

    if not tenant.contactos_pago.filter(estado=EstadoContactoPago.ACTIVE).exists():
        _issue(
            issues,
            code='stage1.arrendatario.contacto_pago_estructurado_faltante',
            entity='Arrendatario',
            entity_id=tenant.pk,
            message='Contrato vigente o futuro requiere al menos un contacto de pago activo estructurado.',
        )

    if tenant.tipo_arrendatario == TipoArrendatario.NATURAL and contrato.politica_documental_id:
        policy = contrato.politica_documental
        if policy.requiere_nacionalidad_arrendatario and not (tenant.nacionalidad or '').strip():
            _issue(
                issues,
                code='stage1.arrendatario.nacionalidad_documental_faltante',
                entity='Arrendatario',
                entity_id=tenant.pk,
                message='La politica documental del contrato exige nacionalidad del arrendatario persona natural.',
            )
        if policy.requiere_estado_civil_arrendatario and not tenant.estado_civil:
            _issue(
                issues,
                code='stage1.arrendatario.estado_civil_documental_faltante',
                entity='Arrendatario',
                entity_id=tenant.pk,
                message='La politica documental del contrato exige estado civil del arrendatario persona natural.',
            )
        if policy.requiere_profesion_arrendatario and not (tenant.profesion or '').strip():
            _issue(
                issues,
                code='stage1.arrendatario.profesion_documental_faltante',
                entity='Arrendatario',
                entity_id=tenant.pk,
                message='La politica documental del contrato exige profesion del arrendatario persona natural.',
            )

    if tenant.tipo_arrendatario == TipoArrendatario.COMPANY:
        representative_snapshot = contrato.snapshot_representante_legal or {}
        if not representative_snapshot:
            _issue(
                issues,
                code='stage1.contrato.representante_legal_snapshot_faltante',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Contrato con arrendatario empresa requiere snapshot de representante legal.',
            )
        elif not isinstance(representative_snapshot, dict):
            _issue(
                issues,
                code='stage1.contrato.representante_legal_snapshot_incompleto',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Snapshot de representante legal debe incluir al menos nombre y RUT.',
            )
        elif not (
            (representative_snapshot.get('nombre') or '').strip()
            and (representative_snapshot.get('rut') or '').strip()
        ):
            _issue(
                issues,
                code='stage1.contrato.representante_legal_snapshot_incompleto',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Snapshot de representante legal debe incluir al menos nombre y RUT.',
            )
        else:
            try:
                normalize_representante_legal_snapshot(representative_snapshot)
            except ValidationError:
                _issue(
                    issues,
                    code='stage1.contrato.representante_legal_snapshot_rut_invalido',
                    entity='Contrato',
                    entity_id=contrato.pk,
                    message='Snapshot de representante legal debe incluir un RUT valido.',
                )


def _audit_contract_document_policy(issues: list[dict[str, Any]], contrato: Contrato) -> None:
    if not contrato.politica_documental_id:
        _issue(
            issues,
            code='stage1.contrato.politica_documental_faltante',
            entity='Contrato',
            entity_id=contrato.pk,
            message='Contrato vigente o futuro requiere politica documental activa de contrato principal.',
        )
        return

    if contrato.politica_documental.tipo_documental != TipoDocumental.MAIN_CONTRACT:
        _issue(
            issues,
            code='stage1.contrato.politica_documental_tipo_invalido',
            entity='Contrato',
            entity_id=contrato.pk,
            message='Contrato vigente o futuro tiene politica documental de tipo distinto a contrato principal.',
        )

    if contrato.politica_documental.estado != EstadoPoliticaFirma.ACTIVE:
        _issue(
            issues,
            code='stage1.contrato.politica_documental_no_activa',
            entity='Contrato',
            entity_id=contrato.pk,
            message='Contrato vigente o futuro tiene politica documental inactiva.',
        )


def _audit_contract_identity_override(issues: list[dict[str, Any]], contrato: Contrato) -> None:
    if not contrato.identidad_envio_override_id:
        return

    identity = contrato.identidad_envio_override
    mandato = contrato.mandato_operacion
    identity_owner = (identity.owner_tipo, identity.owner_id)
    admin_tuple = mandato.administrador_tuple()
    facturadora_tuple = mandato.facturadora_tuple()
    propietario_tuple = mandato.propietario_tuple()

    if identity.estado != EstadoIdentidadEnvio.ACTIVE:
        _issue(
            issues,
            code='stage1.contrato.identidad_override_no_activa',
            entity='Contrato',
            entity_id=contrato.pk,
            message='Contrato vigente o futuro tiene identidad de envio override no activa.',
        )

    if identity_owner not in {admin_tuple, facturadora_tuple}:
        _issue(
            issues,
            code='stage1.contrato.identidad_override_owner_no_autorizado',
            entity='Contrato',
            entity_id=contrato.pk,
            message=(
                'Contrato vigente o futuro usa una identidad override que no pertenece a la entidad '
                'facturadora ni al administrador operativo del mandato.'
            ),
        )

    if identity_owner != propietario_tuple and not mandato.autoriza_comunicacion:
        _issue(
            issues,
            code='stage1.contrato.identidad_override_comunicacion_no_autorizada',
            entity='Contrato',
            entity_id=contrato.pk,
            message=(
                'Contrato vigente o futuro usa identidad override de un actor distinto al propietario sin '
                'autorizacion de comunicacion en el mandato.'
            ),
        )


def _guarantee_covers_key_delivery(garantia: GarantiaContractual) -> bool:
    if garantia.monto_pactado <= Decimal('0.00'):
        return True
    return garantia.monto_recibido >= garantia.monto_pactado or garantia.garantia_parcial_aceptada


def _audit_contract_key_delivery_authorization(
    issues: list[dict[str, Any]],
    contrato: Contrato,
    garantia: GarantiaContractual | None,
) -> None:
    if not contrato.fecha_entrega:
        return

    if contrato.has_key_delivery_authorization():
        if (
            not is_non_sensitive_reference(contrato.entrega_llaves_autorizacion_ref)
            or contains_sensitive_reference(contrato.entrega_llaves_autorizacion_motivo)
        ):
            _issue(
                issues,
                code='stage1.contrato.entrega_llaves_autorizacion_sensible',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Autorizacion de entrega de llaves contiene referencia o motivo sensible.',
            )
        return

    if garantia is None:
        _issue(
            issues,
            code='stage1.contrato.entrega_llaves_sin_garantia_autorizada',
            entity='Contrato',
            entity_id=contrato.pk,
            message='Contrato con entrega de llaves registrada no tiene garantia cubierta ni autorizacion auditada.',
        )
        return

    if not _guarantee_covers_key_delivery(garantia):
        _issue(
            issues,
            code='stage1.contrato.entrega_llaves_garantia_no_cubierta',
            entity='Contrato',
            entity_id=contrato.pk,
            message='Contrato con entrega de llaves registrada tiene garantia incompleta sin autorizacion auditada.',
        )


def _audit_guarantee_history_consistency(
    issues: list[dict[str, Any]],
    garantia: GarantiaContractual,
) -> None:
    if garantia.exceso_garantia_clp > Decimal('0.00'):
        if not garantia.tiene_resolucion_exceso_garantia:
            _issue(
                issues,
                code='stage1.garantia.exceso_sin_resolucion',
                entity='GarantiaContractual',
                entity_id=garantia.pk,
                message=(
                    'Garantia recibida por sobre lo pactado no tiene clasificacion, devolucion, '
                    'regularizacion o bloqueo documentado con evidencia no sensible.'
                ),
            )
        elif (
            not is_non_sensitive_reference(garantia.resolucion_exceso_garantia_ref)
            or contains_sensitive_reference(garantia.resolucion_exceso_garantia_motivo)
        ):
            _issue(
                issues,
                code='stage1.garantia.exceso_resolucion_sensible',
                entity='GarantiaContractual',
                entity_id=garantia.pk,
                message='Resolucion de exceso de garantia contiene referencia o motivo sensible.',
            )

    if garantia.garantia_incompleta:
        _issue(
            issues,
            code='stage1.garantia.parcial_sin_aceptacion',
            entity='GarantiaContractual',
            entity_id=garantia.pk,
            message=(
                'Garantia recibida parcialmente queda incompleta sin referencia formal '
                'de aceptacion parcial.'
            ),
        )

    movements = list(garantia.historial_movimientos.all())
    received_total = sum(
        (movement.monto_clp for movement in movements if movement.tipo_movimiento == TipoMovimientoGarantia.DEPOSIT),
        Decimal('0.00'),
    )
    returned_total = sum(
        (
            movement.monto_clp
            for movement in movements
            if movement.tipo_movimiento
            in {TipoMovimientoGarantia.PARTIAL_RETURN, TipoMovimientoGarantia.TOTAL_RETURN}
        ),
        Decimal('0.00'),
    )
    applied_total = sum(
        (
            movement.monto_clp
            for movement in movements
            if movement.tipo_movimiento
            in {TipoMovimientoGarantia.PARTIAL_RETENTION, TipoMovimientoGarantia.TOTAL_RETENTION}
        ),
        Decimal('0.00'),
    )

    if received_total != garantia.monto_recibido:
        _issue(
            issues,
            code='stage1.garantia.historial_recepcion_inconsistente',
            entity='GarantiaContractual',
            entity_id=garantia.pk,
            message='Monto recibido de garantia no cuadra con historial de depositos.',
        )
    if returned_total != garantia.monto_devuelto:
        _issue(
            issues,
            code='stage1.garantia.historial_devolucion_inconsistente',
            entity='GarantiaContractual',
            entity_id=garantia.pk,
            message='Monto devuelto de garantia no cuadra con historial de devoluciones.',
        )
    if applied_total != garantia.monto_aplicado:
        _issue(
            issues,
            code='stage1.garantia.historial_aplicacion_inconsistente',
            entity='GarantiaContractual',
            entity_id=garantia.pk,
            message='Monto aplicado o retenido de garantia no cuadra con historial de retenciones.',
        )


def _audit_payment_distribution_consistency(issues: list[dict[str, Any]]) -> None:
    payments = PagoMensual.objects.select_related(
        'contrato',
        'contrato__mandato_operacion',
        'periodo_contractual',
    ).prefetch_related('distribuciones_cobro')

    for payment in payments:
        try:
            payment.full_clean()
        except ValidationError as error:
            for message in _validation_messages(error):
                _issue(
                    issues,
                    code='stage1.pago_mensual.validacion_modelo',
                    entity='PagoMensual',
                    entity_id=payment.pk,
                    message=message,
                )

        if payment.contrato.blocks_automatic_past_billing(payment.anio, payment.mes):
            _issue(
                issues,
                code='stage1.pago_mensual.cobro_pasado_retroactivo',
                entity='PagoMensual',
                entity_id=payment.pk,
                message=(
                    'Pago mensual existente corresponde a un cobro pasado generado para un '
                    'contrato retroactivo despues de su fecha de registro operativo.'
                ),
            )

        primary_effective_code = (
            payment.contrato.contrato_propiedades.filter(rol_en_contrato=RolContratoPropiedad.PRIMARY)
            .values_list('codigo_conciliacion_efectivo_snapshot', flat=True)
            .first()
        )
        if primary_effective_code and payment.codigo_conciliacion_efectivo != primary_effective_code:
            _issue(
                issues,
                code='stage1.pago_mensual.codigo_efectivo_desalineado',
                entity='PagoMensual',
                entity_id=payment.pk,
                message=(
                    'Pago mensual existente con CodigoConciliacionEfectivo distinto del codigo '
                    'de la propiedad principal del contrato.'
                ),
            )

        distributions = list(payment.distribuciones_cobro.all())
        month_start = _month_first_day(payment.anio, payment.mes)
        uf_required = payment.periodo_contractual.moneda_base == MonedaBaseContrato.UF
        if not uf_required:
            uf_required = AjusteContrato.objects.filter(
                contrato=payment.contrato,
                activo=True,
                moneda=MonedaBaseContrato.UF,
                mes_inicio__lte=month_start,
                mes_fin__gte=month_start,
            ).exists()
        uf_date = getattr(payment, 'uf_fecha_usada', None)
        uf_value_used = getattr(payment, 'uf_valor_usado', None)
        uf_source_key = str(getattr(payment, 'uf_source_key', '') or '').strip()
        expected_uf_date = payment.fecha_vencimiento
        uf_record = ValorUFDiario.objects.filter(fecha=expected_uf_date).first() if expected_uf_date else None
        if uf_required:
            if not (uf_date and uf_value_used is not None and uf_source_key):
                _issue(
                    issues,
                    code='stage1.pago_mensual.uf_traza_faltante',
                    entity='PagoMensual',
                    entity_id=payment.pk,
                    message='Pago mensual existente calculado en UF no conserva fecha, valor y fuente UF usados.',
                )
            if uf_date and expected_uf_date and uf_date != expected_uf_date:
                _issue(
                    issues,
                    code='stage1.pago_mensual.uf_fecha_desalineada',
                    entity='PagoMensual',
                    entity_id=payment.pk,
                    message='Pago mensual existente conserva una fecha UF distinta a la fecha de vencimiento.',
                )
            if uf_source_key and uf_source_key not in CANONICAL_UF_SOURCE_KEYS:
                _issue(
                    issues,
                    code='stage1.pago_mensual.uf_fuente_no_canonica',
                    entity='PagoMensual',
                    entity_id=payment.pk,
                    message='Pago mensual existente conserva una fuente UF fuera de la cadena canonica.',
                )
        if uf_required and not uf_record:
            _issue(
                issues,
                code='stage1.pago_mensual.uf_valor_faltante',
                entity='PagoMensual',
                entity_id=payment.pk,
                message=(
                    'Pago mensual existente requiere UF, pero no existe ValorUFDiario '
                    f'para {expected_uf_date.isoformat()}.'
                ),
            )
        elif uf_required and uf_record:
            if uf_value_used is not None and Decimal(uf_value_used) != Decimal(uf_record.valor):
                _issue(
                    issues,
                    code='stage1.pago_mensual.uf_valor_desalineado',
                    entity='PagoMensual',
                    entity_id=payment.pk,
                    message='Pago mensual existente conserva un valor UF distinto al ValorUFDiario de la fecha usada.',
                )
            if uf_source_key and uf_source_key != uf_record.source_key:
                _issue(
                    issues,
                    code='stage1.pago_mensual.uf_fuente_desalineada',
                    entity='PagoMensual',
                    entity_id=payment.pk,
                    message='Pago mensual existente conserva una fuente UF distinta al ValorUFDiario de la fecha usada.',
                )

        if not distributions:
            _issue(
                issues,
                code='stage1.pago_mensual.distribuciones_faltantes',
                entity='PagoMensual',
                entity_id=payment.pk,
                message='Pago mensual existente sin DistribucionCobroMensual para validar facturacion esperada.',
            )
            continue

        percentage_total = sum((item.porcentaje_snapshot for item in distributions), Decimal('0.00'))
        accrued_total = sum((item.monto_devengado_clp for item in distributions), Decimal('0.00'))
        reconciled_total = sum((item.monto_conciliado_clp for item in distributions), Decimal('0.00'))
        taxable_total = sum((item.monto_facturable_clp for item in distributions), Decimal('0.00'))

        if percentage_total != Decimal('100.00'):
            _issue(
                issues,
                code='stage1.pago_mensual.distribucion_porcentaje_invalida',
                entity='PagoMensual',
                entity_id=payment.pk,
                message=f'Distribuciones de pago suman {percentage_total}; deben sumar 100.00.',
            )
        if accrued_total != payment.monto_facturable_clp:
            _issue(
                issues,
                code='stage1.pago_mensual.distribucion_devengo_inconsistente',
                entity='PagoMensual',
                entity_id=payment.pk,
                message='Devengo distribuido no cuadra con el monto base del pago mensual.',
            )
        if reconciled_total != payment.monto_pagado_clp:
            _issue(
                issues,
                code='stage1.pago_mensual.distribucion_conciliacion_inconsistente',
                entity='PagoMensual',
                entity_id=payment.pk,
                message='Monto conciliado distribuido no cuadra con el monto pagado del pago mensual.',
            )
        if taxable_total > payment.monto_facturable_clp:
            _issue(
                issues,
                code='stage1.pago_mensual.distribucion_facturable_inconsistente',
                entity='PagoMensual',
                entity_id=payment.pk,
                message='Monto facturable distribuido excede el monto base del pago mensual.',
            )

        billing_company_id = payment.contrato.mandato_operacion.entidad_facturadora_id
        for distribution in distributions:
            if distribution.requiere_dte and distribution.beneficiario_empresa_owner_id != billing_company_id:
                _issue(
                    issues,
                    code='stage1.distribucion_cobro.facturadora_inconsistente',
                    entity='DistribucionCobroMensual',
                    entity_id=distribution.pk,
                    message='Distribucion marcada para DTE no coincide con la entidad facturadora del mandato.',
                )


def _audit_contratos(issues: list[dict[str, Any]]) -> None:
    _audit_model_validation(
        issues,
        queryset=Arrendatario.objects.all(),
        code='stage1.arrendatario.validacion_modelo',
        entity='Arrendatario',
    )
    _audit_model_validation(
        issues,
        queryset=ContactoPagoArrendatario.objects.select_related('arrendatario'),
        code='stage1.contacto_pago.validacion_modelo',
        entity='ContactoPagoArrendatario',
    )
    _audit_model_validation(
        issues,
        queryset=CodeudorSolidario.objects.select_related('contrato'),
        code='stage1.codeudor.validacion_modelo',
        entity='CodeudorSolidario',
    )
    _audit_model_validation(
        issues,
        queryset=AjusteContrato.objects.select_related('contrato'),
        code='stage1.ajuste_contrato.validacion_modelo',
        entity='AjusteContrato',
    )
    _audit_model_validation(
        issues,
        queryset=ValorUFDiario.objects.all(),
        code='stage1.valor_uf.validacion_modelo',
        entity='ValorUFDiario',
    )
    _audit_model_validation(
        issues,
        queryset=HistorialGarantia.objects.select_related(
            'garantia_contractual',
            'movimiento_origen',
        ),
        code='stage1.historial_garantia.validacion_modelo',
        entity='HistorialGarantia',
    )
    _audit_model_validation(
        issues,
        queryset=DistribucionCobroMensual.objects.select_related(
            'pago_mensual',
            'beneficiario_socio_owner',
            'beneficiario_empresa_owner',
        ),
        code='stage1.distribucion_cobro.validacion_modelo',
        entity='DistribucionCobroMensual',
    )
    _audit_model_validation(
        issues,
        queryset=Contrato.objects.select_related(
            'arrendatario',
            'mandato_operacion',
            'mandato_operacion__entidad_facturadora',
            'mandato_operacion__administrador_empresa_owner',
            'mandato_operacion__administrador_socio_owner',
            'mandato_operacion__propietario_empresa_owner',
            'mandato_operacion__propietario_comunidad_owner',
            'mandato_operacion__propietario_socio_owner',
            'identidad_envio_override',
        ),
        code='stage1.contrato.validacion_modelo',
        entity='Contrato',
    )
    _audit_model_validation(
        issues,
        queryset=ContratoPropiedad.objects.select_related('contrato', 'propiedad'),
        code='stage1.contrato_propiedad.validacion_modelo',
        entity='ContratoPropiedad',
    )
    _audit_model_validation(
        issues,
        queryset=PeriodoContractual.objects.select_related('contrato'),
        code='stage1.periodo.validacion_modelo',
        entity='PeriodoContractual',
    )
    _audit_model_validation(
        issues,
        queryset=AvisoTermino.objects.select_related('contrato'),
        code='stage1.aviso_termino.validacion_modelo',
        entity='AvisoTermino',
    )
    _audit_model_validation(
        issues,
        queryset=GarantiaContractual.objects.select_related('contrato'),
        code='stage1.garantia.validacion_modelo',
        entity='GarantiaContractual',
    )
    _audit_payment_distribution_consistency(issues)
    _audit_early_termination_proration(issues)
    _audit_late_termination_notices(issues)

    duplicate_any_role = (
        ContratoPropiedad.objects.filter(contrato__estado__in=ACTIVE_CONTRACT_STATES)
        .values('propiedad_id', 'contrato__estado')
        .annotate(total=Count('contrato_id', distinct=True))
        .filter(total__gt=1)
    )
    for row in duplicate_any_role:
        _issue(
            issues,
            code='stage1.propiedad.contratos_duplicados',
            entity='Propiedad',
            entity_id=row['propiedad_id'],
            message=(
                f'Propiedad participa en {row["total"]} contratos {row["contrato__estado"]}; '
                'maximo uno por estado, incluyendo propiedades vinculadas.'
            ),
        )

    duplicate_primary = (
        ContratoPropiedad.objects.filter(
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            contrato__estado__in=ACTIVE_CONTRACT_STATES,
        )
        .values('propiedad_id', 'contrato__estado')
        .annotate(total=Count('contrato_id', distinct=True))
        .filter(total__gt=1)
    )
    for row in duplicate_primary:
        _issue(
            issues,
            code='stage1.propiedad.contratos_primarios_duplicados',
            entity='Propiedad',
            entity_id=row['propiedad_id'],
            message=f'Propiedad con {row["total"]} contratos {row["contrato__estado"]} como principal; maximo uno por estado.',
        )

    duplicate_effective_codes = (
        ContratoPropiedad.objects.filter(
            contrato__estado__in=ACTIVE_CONTRACT_STATES,
        )
        .values(
            'contrato__mandato_operacion__cuenta_recaudadora_id',
            'contrato__estado',
            'codigo_conciliacion_efectivo_snapshot',
        )
        .annotate(total=Count('contrato_id', distinct=True))
        .filter(total__gt=1)
    )
    for row in duplicate_effective_codes:
        _issue(
            issues,
            code='stage1.codigo_efectivo.duplicado_en_cuenta',
            entity='CuentaRecaudadora',
            entity_id=row['contrato__mandato_operacion__cuenta_recaudadora_id'],
            message=(
                f'Codigo efectivo {row["codigo_conciliacion_efectivo_snapshot"]} usado en '
                f'{row["total"]} contratos {row["contrato__estado"]} de la misma cuenta recaudadora.'
            ),
        )

    contracts = Contrato.objects.filter(estado__in=ACTIVE_CONTRACT_STATES).select_related(
        'arrendatario',
        'mandato_operacion',
        'mandato_operacion__entidad_facturadora',
        'mandato_operacion__administrador_empresa_owner',
        'mandato_operacion__administrador_socio_owner',
        'mandato_operacion__propietario_empresa_owner',
        'mandato_operacion__propietario_comunidad_owner',
        'mandato_operacion__propietario_socio_owner',
        'mandato_operacion__propiedad',
        'identidad_envio_override',
        'politica_documental',
    )
    for contrato in contracts:
        if contrato.fecha_inicio.day != 1:
            _issue(
                issues,
                code='stage1.contrato.inicio_no_mensual',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Contrato activo/futuro debe iniciar el dia 1.',
            )
        if contrato.fecha_fin_vigente.day != _month_last_day(contrato.fecha_fin_vigente.year, contrato.fecha_fin_vigente.month):
            _issue(
                issues,
                code='stage1.contrato.fin_no_mensual',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Contrato activo/futuro debe terminar el ultimo dia del mes.',
            )
        if contrato.mandato_operacion.estado != EstadoMandatoOperacion.ACTIVE:
            _issue(
                issues,
                code='stage1.contrato.mandato_no_activo',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Contrato vigente o futuro requiere mandato operativo activo.',
            )
        if contrato.mandato_operacion.vigencia_desde > contrato.fecha_inicio:
            _issue(
                issues,
                code='stage1.contrato.mandato_no_vigente_al_inicio',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Contrato vigente o futuro inicia antes de la vigencia del mandato operativo.',
            )
        if (
            contrato.mandato_operacion.vigencia_hasta
            and contrato.mandato_operacion.vigencia_hasta < contrato.fecha_fin_vigente
        ):
            _issue(
                issues,
                code='stage1.contrato.mandato_no_cubre_fin',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Contrato vigente o futuro termina despues de la vigencia del mandato operativo.',
            )
        active_channel_exists = AsignacionCanalOperacion.objects.filter(
            mandato_operacion=contrato.mandato_operacion,
            estado=EstadoAsignacionCanal.ACTIVE,
            identidad_envio__estado=EstadoIdentidadEnvio.ACTIVE,
        ).exists()
        if not active_channel_exists:
            _issue(
                issues,
                code='stage1.contrato.canal_operativo_faltante',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Contrato vigente o futuro requiere al menos un canal operativo activo en su mandato.',
            )

        if contrato.requires_retroactive_manual_notification():
            _issue(
                issues,
                code='stage1.contrato.notificacion_manual_retroactiva',
                entity='Contrato',
                entity_id=contrato.pk,
                message=contrato.retroactive_manual_notification_alert(),
                severity='warning',
            )

        _audit_contract_document_policy(issues, contrato)
        _audit_contract_tenant_readiness(issues, contrato)
        _audit_contract_identity_override(issues, contrato)

        links = list(contrato.contrato_propiedades.select_related('propiedad'))

        primary_links = [link for link in links if link.rol_en_contrato == RolContratoPropiedad.PRIMARY]
        primary_property_id = None
        if len(primary_links) != 1:
            _issue(
                issues,
                code='stage1.contrato.propiedad_principal_invalida',
                entity='Contrato',
                entity_id=contrato.pk,
                message=f'Contrato vigente/futuro con {len(primary_links)} propiedades principales; debe tener exactamente una.',
            )
        else:
            primary_property_id = primary_links[0].propiedad_id
            if primary_property_id != contrato.mandato_operacion.propiedad_id:
                _issue(
                    issues,
                    code='stage1.contrato.propiedad_principal_no_mandato',
                    entity='Contrato',
                    entity_id=contrato.pk,
                    message='La propiedad principal del contrato no coincide con la propiedad del mandato operativo.',
                )
            if contrato.tiene_gastos_comunes:
                has_structured_common_expense = ServicioPropiedad.objects.filter(
                    propiedad_id=primary_property_id,
                    tipo_servicio=TipoServicioPropiedad.COMMON_EXPENSES,
                    activo=True,
                ).exists()
                if not has_structured_common_expense:
                    _issue(
                        issues,
                        code='stage1.propiedad.gasto_comun_estructurado_faltante',
                        entity='Propiedad',
                        entity_id=primary_property_id,
                        message=(
                            'Contrato vigente o futuro con gastos comunes requiere servicio de gasto comun '
                            'activo y estructurado para la propiedad principal.'
                        ),
                    )

        _audit_future_contract_closure_evidence(
            issues,
            contrato=contrato,
            primary_property_id=primary_property_id,
        )

        distribution_total = sum((link.porcentaje_distribucion_interna for link in links), Decimal('0.00'))
        if links and distribution_total != Decimal('100.00'):
            _issue(
                issues,
                code='stage1.contrato.distribucion_propiedades_invalida',
                entity='Contrato',
                entity_id=contrato.pk,
                message=f'La distribucion interna de propiedades suma {distribution_total}; debe sumar 100.00.',
            )

        _audit_contract_periods(issues, contrato)

        garantia = None
        try:
            garantia = contrato.garantia_contractual
        except GarantiaContractual.DoesNotExist:
            _issue(
                issues,
                code='stage1.contrato.garantia_faltante',
                entity='Contrato',
                entity_id=contrato.pk,
                message='Contrato vigente o futuro sin GarantiaContractual registrada.',
            )
        else:
            _audit_guarantee_history_consistency(issues, garantia)
        _audit_contract_key_delivery_authorization(issues, contrato, garantia)


def collect_stage1_matrix_audit(
    *,
    source_kind: str = 'local',
    source_label: str = '',
    authorization_ref: str = '',
    responsible_ref: str = '',
    require_data: bool = False,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    raw_source_label = (source_label or '').strip()
    raw_authorization_ref = (authorization_ref or '').strip()
    raw_responsible_ref = (responsible_ref or '').strip()
    safe_source_label = _safe_source_label(source_label)
    safe_authorization_ref = _safe_reference(authorization_ref)
    safe_responsible_ref = _safe_reference(responsible_ref)
    summary = _build_summary()
    has_required_data = _has_required_stage1_data(summary)

    _audit_evidence_source_metadata(
        issues,
        source_kind=source_kind,
        source_label=raw_source_label,
        authorization_ref=raw_authorization_ref,
        responsible_ref=raw_responsible_ref,
    )

    if require_data and not has_required_data:
        _issue(
            issues,
            code='stage1.data_missing',
            entity='Stage1Matrix',
            message='La base auditada no contiene todos los agregados minimos para cerrar la matriz Etapa 1.',
        )

    _audit_patrimonio(issues)
    _audit_operacion(issues)
    _audit_facturacion(issues)
    _audit_contratos(issues)

    issue_counts = defaultdict(int)
    for issue in issues:
        issue_counts[issue['severity']] += 1

    blocking_count = issue_counts['blocking']
    evidence_grade = source_kind in EVIDENCE_GRADE_SOURCE_KINDS
    gate_passed = blocking_count == 0 and has_required_data and evidence_grade
    aggregate_classification = _build_aggregate_classification(
        summary=summary,
        issues=issues,
        has_required_data=has_required_data,
        evidence_grade=evidence_grade,
        require_data=require_data,
    )

    issue_codes = {issue['code'] for issue in issues}
    if blocking_count and issue_codes == {'stage1.data_missing'}:
        classification = 'bloqueado_dato_real'
    elif blocking_count:
        classification = 'defectuoso'
    elif not has_required_data:
        classification = 'bloqueado_dato_real' if require_data else 'implementado_sin_evidencia'
    elif not evidence_grade:
        classification = 'implementado_sin_evidencia'
    else:
        classification = 'resuelto_confirmado'

    return {
        'stage': 'Etapa 1 - Datos reales y matriz base',
        'source_kind': source_kind,
        'source_label': safe_source_label,
        'authorization_ref': safe_authorization_ref,
        'responsible_ref': safe_responsible_ref,
        'require_data': require_data,
        'summary': summary,
        'aggregate_classification': aggregate_classification,
        'has_required_stage1_data': has_required_data,
        'evidence_grade': evidence_grade,
        'classification': classification,
        'ready_for_stage1_close': gate_passed,
        'issue_counts': dict(issue_counts),
        'issues': issues,
    }
