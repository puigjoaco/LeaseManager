from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Count

from cobranza.models import GarantiaContractual
from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoRegistro
from contratos.models import (
    Arrendatario,
    Contrato,
    ContratoPropiedad,
    EstadoContrato,
    MonedaBaseContrato,
    PeriodoContractual,
    RolContratoPropiedad,
)
from operacion.models import CuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import ComunidadPatrimonial, Empresa, Propiedad, Socio


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


def _month_last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _has_required_stage1_data(summary: dict[str, int]) -> bool:
    required_positive_counts = (
        'socios',
        'empresas',
        'comunidades',
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


def _build_summary() -> dict[str, int]:
    socios_count = Socio.objects.count()
    empresas_count = Empresa.objects.count()
    comunidades_count = ComunidadPatrimonial.objects.count()
    return {
        'socios': socios_count,
        'empresas': empresas_count,
        'comunidades': comunidades_count,
        'owner_entities': socios_count + empresas_count + comunidades_count,
        'propiedades': Propiedad.objects.count(),
        'cuentas_recaudadoras': CuentaRecaudadora.objects.count(),
        'mandatos': MandatoOperacion.objects.count(),
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

    for propiedad in Propiedad.objects.filter(estado='activa').select_related('empresa_owner', 'comunidad_owner', 'socio_owner'):
        active_mandates_count = propiedad.mandatos_operacion.filter(estado=EstadoMandatoOperacion.ACTIVE).count()
        if active_mandates_count != 1:
            _issue(
                issues,
                code='stage1.propiedad.mandato_activo_invalido',
                entity='Propiedad',
                entity_id=propiedad.pk,
                message=f'Propiedad activa con {active_mandates_count} mandatos activos; debe tener exactamente uno.',
            )
        try:
            propiedad.full_clean()
        except ValidationError as error:
            for message in _validation_messages(error):
                _issue(
                    issues,
                    code='stage1.propiedad.validacion_modelo',
                    entity='Propiedad',
                    entity_id=propiedad.pk,
                    message=message,
                )


def _audit_operacion(issues: list[dict[str, Any]]) -> None:
    for cuenta in CuentaRecaudadora.objects.filter(estado_operativo='activa').select_related(
        'empresa_owner',
        'comunidad_owner',
        'socio_owner',
    ):
        try:
            cuenta.full_clean()
        except ValidationError as error:
            for message in _validation_messages(error):
                _issue(
                    issues,
                    code='stage1.cuenta.validacion_modelo',
                    entity='CuentaRecaudadora',
                    entity_id=cuenta.pk,
                    message=message,
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


def _audit_contratos(issues: list[dict[str, Any]]) -> None:
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

    contracts = Contrato.objects.filter(estado__in=ACTIVE_CONTRACT_STATES).select_related(
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

        links = list(contrato.contrato_propiedades.select_related('propiedad'))
        primary_links = [link for link in links if link.rol_en_contrato == RolContratoPropiedad.PRIMARY]
        if len(primary_links) != 1:
            _issue(
                issues,
                code='stage1.contrato.propiedad_principal_invalida',
                entity='Contrato',
                entity_id=contrato.pk,
                message=f'Contrato vigente/futuro con {len(primary_links)} propiedades principales; debe tener exactamente una.',
            )
        elif primary_links[0].propiedad_id != contrato.mandato_operacion.propiedad_id:
            _issue(
                issues,
                code='stage1.contrato.propiedad_principal_no_mandato',
                entity='Contrato',
                entity_id=contrato.pk,
                message='La propiedad principal del contrato no coincide con la propiedad del mandato operativo.',
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
