from __future__ import annotations

import calendar
import re
import unicodedata
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Count

from cobranza.models import GarantiaContractual
from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoRegistro, RegimenTributarioEmpresa
from contratos.models import (
    Arrendatario,
    AvisoTermino,
    Contrato,
    ContratoPropiedad,
    EstadoContactoArrendatario,
    EstadoAvisoTermino,
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
ACTIVE_CONTRACT_STATES = {EstadoContrato.ACTIVE, EstadoContrato.FUTURE}


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


def _has_required_stage1_data(summary: dict[str, int]) -> bool:
    required_positive_counts = (
        'socios',
        'empresas',
        'comunidades',
        'participaciones_patrimoniales',
        'representaciones_comunidad',
        'propiedades',
        'cuentas_recaudadoras',
        'mandatos',
        'arrendatarios',
        'contratos',
        'contrato_propiedades',
        'periodos_contractuales',
        'garantias_contractuales',
        'mandatos_con_facturacion',
        'configuraciones_fiscales_activas',
    )
    return all(summary[count_name] > 0 for count_name in required_positive_counts)


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
        'contratos': Contrato.objects.count(),
        'contratos_activos_o_futuros': Contrato.objects.filter(estado__in=ACTIVE_CONTRACT_STATES).count(),
        'contrato_propiedades': ContratoPropiedad.objects.count(),
        'periodos_contractuales': PeriodoContractual.objects.count(),
        'garantias_contractuales': GarantiaContractual.objects.count(),
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
        try:
            period.full_clean()
        except ValidationError as error:
            for message in _validation_messages(error):
                _issue(
                    issues,
                    code='stage1.periodo.validacion_modelo',
                    entity='PeriodoContractual',
                    entity_id=period.pk,
                    message=message,
                )
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


def _audit_contratos(issues: list[dict[str, Any]]) -> None:
    _audit_model_validation(
        issues,
        queryset=Arrendatario.objects.all(),
        code='stage1.arrendatario.validacion_modelo',
        entity='Arrendatario',
    )

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
        try:
            contrato.full_clean()
        except ValidationError as error:
            for message in _validation_messages(error):
                _issue(
                    issues,
                    code='stage1.contrato.validacion_modelo',
                    entity='Contrato',
                    entity_id=contrato.pk,
                    message=message,
                )
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
        for link in links:
            try:
                link.full_clean()
            except ValidationError as error:
                for message in _validation_messages(error):
                    _issue(
                        issues,
                        code='stage1.contrato_propiedad.validacion_modelo',
                        entity='ContratoPropiedad',
                        entity_id=link.pk,
                        message=message,
                    )

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
            try:
                garantia.full_clean()
            except ValidationError as error:
                for message in _validation_messages(error):
                    _issue(
                        issues,
                        code='stage1.garantia.validacion_modelo',
                        entity='GarantiaContractual',
                        entity_id=garantia.pk,
                        message=message,
                    )


def collect_stage1_matrix_audit(
    *,
    source_kind: str = 'local',
    source_label: str = '',
    require_data: bool = False,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    summary = _build_summary()
    has_required_data = _has_required_stage1_data(summary)

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
        'source_label': source_label,
        'require_data': require_data,
        'summary': summary,
        'has_required_stage1_data': has_required_data,
        'evidence_grade': evidence_grade,
        'classification': classification,
        'ready_for_stage1_close': gate_passed,
        'issue_counts': dict(issue_counts),
        'issues': issues,
    }
