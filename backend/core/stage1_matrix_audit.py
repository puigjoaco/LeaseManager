from __future__ import annotations

import calendar
import re
import unicodedata
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Count

from cobranza.models import (
    AjusteContrato,
    DistribucionCobroMensual,
    GarantiaContractual,
    HistorialGarantia,
    PagoMensual,
    TipoMovimientoGarantia,
    ValorUFDiario,
)
from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoRegistro, RegimenTributarioEmpresa
from contratos.models import (
    Arrendatario,
    AvisoTermino,
    CodeudorSolidario,
    Contrato,
    ContratoPropiedad,
    EstadoContactoArrendatario,
    EstadoAvisoTermino,
    EstadoCodeudorSolidario,
    EstadoContrato,
    MonedaBaseContrato,
    PeriodoContractual,
    RolContratoPropiedad,
    TipoArrendatario,
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
    ParticipacionPatrimonial,
    Propiedad,
    RepresentacionComunidad,
    Socio,
)


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
        'entities': {'Propiedad'},
        'code_prefixes': ('stage1.propiedad.',),
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
        'entities': {'Arrendatario'},
        'code_prefixes': ('stage1.arrendatario.',),
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


def _issue_matches_aggregate(issue: dict[str, Any], definition: dict[str, Any]) -> bool:
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
        'cuentas_recaudadoras': CuentaRecaudadora.objects.count(),
        'mandatos': MandatoOperacion.objects.count(),
        'identidades_envio_activas': IdentidadDeEnvio.objects.filter(estado=EstadoIdentidadEnvio.ACTIVE).count(),
        'asignaciones_canal_activas': AsignacionCanalOperacion.objects.filter(
            estado=EstadoAsignacionCanal.ACTIVE
        ).count(),
        'arrendatarios': Arrendatario.objects.count(),
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
        active_mandates_count = propiedad.mandatos_operacion.filter(estado=EstadoMandatoOperacion.ACTIVE).count()
        if active_mandates_count != 1:
            _issue(
                issues,
                code='stage1.propiedad.mandato_activo_invalido',
                entity='Propiedad',
                entity_id=propiedad.pk,
                message=f'Propiedad activa con {active_mandates_count} mandatos activos; debe tener exactamente uno.',
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
        aviso_exists = AvisoTermino.objects.filter(
            contrato=current_contract,
            estado=EstadoAvisoTermino.REGISTERED,
            fecha_efectiva__lte=contrato.fecha_inicio,
        ).exists()
        if not aviso_exists:
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

    if not (tenant.domicilio_notificaciones or '').strip():
        _issue(
            issues,
            code='stage1.arrendatario.domicilio_notificaciones_faltante',
            entity='Arrendatario',
            entity_id=tenant.pk,
            message='Contrato vigente o futuro requiere domicilio de notificaciones del arrendatario.',
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


def _audit_guarantee_history_consistency(
    issues: list[dict[str, Any]],
    garantia: GarantiaContractual,
) -> None:
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
        if uf_required and not ValorUFDiario.objects.filter(fecha=month_start).exists():
            _issue(
                issues,
                code='stage1.pago_mensual.uf_valor_faltante',
                entity='PagoMensual',
                entity_id=payment.pk,
                message=(
                    'Pago mensual existente requiere UF, pero no existe ValorUFDiario '
                    f'para {month_start.isoformat()}.'
                ),
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
        queryset=Contrato.objects.select_related('arrendatario', 'mandato_operacion'),
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
        'mandato_operacion__propiedad',
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

        _audit_contract_tenant_readiness(issues, contrato)

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
