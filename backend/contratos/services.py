import calendar
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audit.models import ManualResolution
from audit.services import create_audit_event
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference

from .models import (
    AUTOMATIC_RENEWAL_EVENT_TYPE,
    AUTOMATIC_RENEWAL_ORIGIN,
    Arrendatario,
    AvisoTermino,
    Contrato,
    ContratoPropiedad,
    EstadoAvisoTermino,
    EstadoContrato,
    MonedaBaseContrato,
    PeriodoContractual,
    RENEWAL_PERIOD_KIND,
    TENANT_REPLACEMENT_EVENT_TYPE,
    WHATSAPP_BLOCK_ALERT_CATEGORY,
    WHATSAPP_BLOCK_EVENT_TYPE,
    WHATSAPP_REHABILITATION_EVENT_TYPE,
)


def _last_day_of_month(value):
    return calendar.monthrange(value.year, value.month)[1]


def _validate_month_end(field_name, value):
    if value.day != _last_day_of_month(value):
        raise ValidationError({field_name: 'La renovacion automatica debe terminar el ultimo dia del mes.'})


def _validate_amount(moneda_base, monto_base):
    if moneda_base == MonedaBaseContrato.CLP and monto_base < Decimal('1000.00'):
        raise ValidationError({'monto_base': 'Un periodo CLP debe respetar el minimo operativo de 1.000.'})
    if moneda_base == MonedaBaseContrato.UF and monto_base <= Decimal('0.00'):
        raise ValidationError({'monto_base': 'Un periodo UF debe tener monto positivo.'})


def _validate_renewal_base_policy(*, base_changed, policy_ref, policy_reason):
    if not base_changed:
        return
    if not policy_ref or not policy_reason:
        raise ValidationError(
            {
                'politica_base_renovacion_ref': (
                    'Una renovacion con base distinta al ultimo tramo vigente requiere politica documentada.'
                )
            }
        )
    if not is_non_sensitive_reference(policy_ref):
        raise ValidationError(
            {
                'politica_base_renovacion_ref': (
                    'La politica de base de renovacion debe usar una referencia no sensible.'
                )
            }
        )
    if contains_sensitive_reference(policy_reason):
        raise ValidationError(
            {
                'politica_base_renovacion_motivo': (
                    'La politica de base de renovacion no debe contener referencias sensibles.'
                )
            }
        )


def _require_audit_actor(message, *, actor_user=None, actor_identifier=''):
    actor_identifier = str(actor_identifier or '').strip()
    if actor_user is None and not actor_identifier:
        raise ValueError(message)
    return actor_identifier


def create_whatsapp_block_trace(
    *,
    tenant,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    actor_identifier = _require_audit_actor(
        'El bloqueo definitivo de WhatsApp requiere un actor trazable para auditoria.',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
    )
    metadata = {
        'arrendatario_id': tenant.pk,
        'motivo': tenant.whatsapp_bloqueo_motivo,
        'evidencia_ref': tenant.whatsapp_bloqueo_evidencia_ref,
        'whatsapp_bloqueado_at': tenant.whatsapp_bloqueado_at.isoformat() if tenant.whatsapp_bloqueado_at else '',
    }
    if actor_identifier:
        metadata['actor_identifier'] = actor_identifier
    alert = ManualResolution.objects.create(
        category=WHATSAPP_BLOCK_ALERT_CATEGORY,
        scope_type='arrendatario',
        scope_reference=str(tenant.pk),
        summary='Bloqueo definitivo de WhatsApp requiere seguimiento administrativo.',
        rationale=tenant.whatsapp_bloqueo_motivo,
        requested_by=actor_user,
        metadata=metadata,
    )
    event = create_audit_event(
        event_type=WHATSAPP_BLOCK_EVENT_TYPE,
        severity='warning',
        entity_type='arrendatario',
        entity_id=str(tenant.pk),
        summary='Se registro bloqueo definitivo de WhatsApp para el arrendatario.',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
        metadata=metadata,
    )
    return alert, event


def resolve_whatsapp_block_alerts(
    *,
    tenant,
    rehabilitacion_ref: str,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    actor_identifier = _require_audit_actor(
        'La rehabilitacion manual de WhatsApp requiere un actor trazable para auditoria.',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
    )
    if tenant.whatsapp_rehabilitado_at is None:
        tenant.whatsapp_rehabilitado_at = timezone.now()
        tenant.full_clean()
        tenant.save(update_fields=['whatsapp_rehabilitado_at', 'updated_at'])
    open_alerts = list(
        ManualResolution.objects.filter(
            category=WHATSAPP_BLOCK_ALERT_CATEGORY,
            scope_type='arrendatario',
            scope_reference=str(tenant.pk),
            status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW],
        )
    )
    resolved_at = timezone.now()
    for alert in open_alerts:
        alert.status = ManualResolution.Status.RESOLVED
        alert.resolved_at = resolved_at
        alert.resolved_by = actor_user
        metadata = alert.metadata if isinstance(alert.metadata, dict) else {}
        alert.metadata = {
            **metadata,
            'rehabilitacion_ref': rehabilitacion_ref,
            'whatsapp_rehabilitado_at': tenant.whatsapp_rehabilitado_at.isoformat()
            if tenant.whatsapp_rehabilitado_at
            else '',
            'resolved_actor_identifier': actor_identifier,
        }
        alert.save(update_fields=['status', 'resolved_at', 'resolved_by', 'metadata'])
    event = create_audit_event(
        event_type=WHATSAPP_REHABILITATION_EVENT_TYPE,
        entity_type='arrendatario',
        entity_id=str(tenant.pk),
        summary='Se registro rehabilitacion manual de WhatsApp para el arrendatario.',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
        metadata={
            'arrendatario_id': tenant.pk,
            'rehabilitacion_ref': rehabilitacion_ref,
            'whatsapp_rehabilitado_at': tenant.whatsapp_rehabilitado_at.isoformat()
            if tenant.whatsapp_rehabilitado_at
            else '',
            'alertas_resueltas': len(open_alerts),
        },
    )
    return open_alerts, event


@transaction.atomic
def block_whatsapp_contact(
    *,
    tenant,
    motivo,
    evidencia_ref,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    tenant = Arrendatario.objects.select_for_update().get(pk=tenant.pk)
    actor_identifier = _require_audit_actor(
        'El bloqueo definitivo de WhatsApp requiere un actor trazable para auditoria.',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
    )
    tenant.block_whatsapp(motivo=motivo, evidencia_ref=evidencia_ref)
    tenant.save(
        update_fields=[
            'whatsapp_opt_in',
            'whatsapp_bloqueado',
            'whatsapp_bloqueo_motivo',
            'whatsapp_bloqueo_evidencia_ref',
            'whatsapp_bloqueado_at',
            'whatsapp_rehabilitacion_ref',
            'whatsapp_rehabilitado_at',
            'updated_at',
        ]
    )
    alert, event = create_whatsapp_block_trace(
        tenant=tenant,
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
    )
    return tenant, alert, event


@transaction.atomic
def rehabilitate_whatsapp_contact(
    *,
    tenant,
    rehabilitacion_ref,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    tenant = Arrendatario.objects.select_for_update().get(pk=tenant.pk)
    actor_identifier = _require_audit_actor(
        'La rehabilitacion manual de WhatsApp requiere un actor trazable para auditoria.',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
    )
    tenant.rehabilitate_whatsapp(rehabilitacion_ref=rehabilitacion_ref)
    tenant.save(
        update_fields=[
            'whatsapp_bloqueado',
            'whatsapp_rehabilitacion_ref',
            'whatsapp_rehabilitado_at',
            'updated_at',
        ]
    )
    alerts, event = resolve_whatsapp_block_alerts(
        tenant=tenant,
        rehabilitacion_ref=rehabilitacion_ref,
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
    )
    return tenant, alerts, event


def _contract_property_payload(contract):
    links = list(contract.contrato_propiedades.order_by('rol_en_contrato', 'id'))
    if not links:
        raise ValidationError({'contrato_propiedades': 'El cambio de arrendatario requiere propiedades contractuales.'})
    return [
        {
            'propiedad': link.propiedad,
            'rol_en_contrato': link.rol_en_contrato,
            'porcentaje_distribucion_interna': link.porcentaje_distribucion_interna,
            'codigo_conciliacion_efectivo_snapshot': link.codigo_conciliacion_efectivo_snapshot,
        }
        for link in links
    ]


def _base_period_for_replacement(contract, replacement_start):
    return (
        contract.periodos_contractuales.filter(fecha_inicio__lt=replacement_start)
        .order_by('-fecha_fin', '-numero_periodo')
        .first()
    )


def _validate_replacement_notice_conflict(*, aviso, future_start):
    if not aviso.has_executed_renewal_conflict(future_start):
        return
    if not aviso.has_renewal_conflict_resolution() or not is_non_sensitive_reference(
        aviso.resolucion_conflicto_renovacion_ref
    ):
        raise ValidationError(
            {
                'resolucion_conflicto_renovacion_ref': (
                    'Existe conflicto entre aviso, renovacion ya ejecutada y contrato futuro; '
                    'se requiere resolucion guiada con referencia no sensible y motivo trazable.'
                )
            }
        )


@transaction.atomic
def execute_automatic_contract_renewal(
    *,
    contract,
    fecha_fin,
    monto_base=None,
    moneda_base='',
    politica_base_renovacion_ref='',
    politica_base_renovacion_motivo='',
    actor_user=None,
    ip_address=None,
):
    contract = (
        Contrato.objects.select_for_update()
        .select_related('mandato_operacion', 'arrendatario', 'politica_documental')
        .get(pk=contract.pk)
    )
    if contract.estado != EstadoContrato.ACTIVE:
        raise ValidationError({'estado': 'Solo un contrato vigente puede renovarse automaticamente.'})

    if AvisoTermino.objects.filter(
        contrato=contract,
        estado=EstadoAvisoTermino.REGISTERED,
    ).exists():
        raise ValidationError({'aviso_termino': 'Un AvisoTermino registrado bloquea la renovacion automatica.'})

    previous_period = contract.periodos_contractuales.order_by('-fecha_fin', '-numero_periodo').first()
    if previous_period is None:
        raise ValidationError({'periodos_contractuales': 'La renovacion automatica requiere un tramo vigente base.'})
    if previous_period.fecha_fin != contract.fecha_fin_vigente:
        raise ValidationError(
            {
                'periodos_contractuales': (
                    'La renovacion automatica requiere que el ultimo tramo cubra la fecha fin vigente.'
                )
            }
        )

    renewal_start = contract.fecha_fin_vigente + timedelta(days=1)
    if renewal_start.day != 1:
        raise ValidationError(
            {'fecha_inicio': 'La renovacion automatica debe iniciar el primer dia del mes siguiente.'}
        )
    if fecha_fin < renewal_start:
        raise ValidationError({'fecha_fin': 'La fecha fin de renovacion no puede ser anterior al inicio renovado.'})
    _validate_month_end('fecha_fin', fecha_fin)

    renewal_amount = Decimal(monto_base) if monto_base is not None else previous_period.monto_base
    renewal_currency = moneda_base or previous_period.moneda_base
    _validate_amount(renewal_currency, renewal_amount)

    policy_ref = str(politica_base_renovacion_ref or '').strip()
    policy_reason = str(politica_base_renovacion_motivo or '').strip()
    base_changed = (
        renewal_currency != previous_period.moneda_base
        or Decimal(renewal_amount) != Decimal(previous_period.monto_base)
    )
    _validate_renewal_base_policy(
        base_changed=base_changed,
        policy_ref=policy_ref,
        policy_reason=policy_reason,
    )

    previous_contract_end = contract.fecha_fin_vigente
    next_period_number = previous_period.numero_periodo + 1
    contract.fecha_fin_vigente = fecha_fin
    contract.tiene_tramos = True
    contract.full_clean()
    contract.save(update_fields=['fecha_fin_vigente', 'tiene_tramos', 'updated_at'])

    renewal_period = PeriodoContractual(
        contrato=contract,
        numero_periodo=next_period_number,
        fecha_inicio=renewal_start,
        fecha_fin=fecha_fin,
        monto_base=renewal_amount,
        moneda_base=renewal_currency,
        tipo_periodo=RENEWAL_PERIOD_KIND,
        origen_periodo=AUTOMATIC_RENEWAL_ORIGIN,
        politica_base_renovacion_ref=policy_ref,
        politica_base_renovacion_motivo=policy_reason,
    )
    renewal_period._allow_automatic_renewal_trace = True
    renewal_period.full_clean()
    renewal_period.save()

    create_audit_event(
        event_type=AUTOMATIC_RENEWAL_EVENT_TYPE,
        entity_type='periodo_contractual',
        entity_id=str(renewal_period.pk),
        summary='Se ejecuto renovacion automatica de contrato por PeriodoContractual.',
        actor_user=actor_user,
        ip_address=ip_address,
        metadata={
            'contrato_id': contract.pk,
            'codigo_contrato': contract.codigo_contrato,
            'periodo_contractual_id': renewal_period.pk,
            'numero_periodo': renewal_period.numero_periodo,
            'fecha_fin_anterior': previous_contract_end.isoformat(),
            'fecha_inicio_renovacion': renewal_start.isoformat(),
            'fecha_fin_renovacion': fecha_fin.isoformat(),
            'base_modificada': base_changed,
            'politica_base_renovacion_ref': policy_ref,
        },
    )
    return renewal_period


@transaction.atomic
def execute_tenant_replacement(
    *,
    contract,
    arrendatario,
    codigo_contrato,
    fecha_inicio,
    fecha_fin_vigente,
    causal_aviso,
    monto_base=None,
    moneda_base='',
    dia_pago_mensual=None,
    plazo_notificacion_termino_dias=None,
    dias_prealerta_admin=None,
    politica_documental=None,
    identidad_envio_override=None,
    tiene_gastos_comunes=None,
    snapshot_representante_legal=None,
    resolucion_conflicto_renovacion_ref='',
    resolucion_conflicto_renovacion_motivo='',
    actor_user=None,
    ip_address=None,
):
    contract = (
        Contrato.objects.select_for_update()
        .select_related('mandato_operacion', 'arrendatario', 'politica_documental', 'identidad_envio_override')
        .prefetch_related('contrato_propiedades', 'periodos_contractuales')
        .get(pk=contract.pk)
    )
    if contract.estado != EstadoContrato.ACTIVE:
        raise ValidationError({'estado': 'Solo un contrato vigente puede ejecutar cambio de arrendatario.'})
    if arrendatario.pk == contract.arrendatario_id:
        raise ValidationError({'arrendatario': 'El nuevo arrendatario debe ser distinto al contrato vigente.'})
    if fecha_inicio <= contract.fecha_inicio:
        raise ValidationError({'fecha_inicio': 'El contrato nuevo debe iniciar despues del contrato vigente.'})
    if fecha_inicio.day != 1:
        raise ValidationError({'fecha_inicio': 'El contrato nuevo debe iniciar el primer dia del mes.'})
    if fecha_fin_vigente < fecha_inicio:
        raise ValidationError({'fecha_fin_vigente': 'La fecha fin del contrato nuevo no puede ser anterior al inicio.'})
    _validate_month_end('fecha_fin_vigente', fecha_fin_vigente)
    if AvisoTermino.objects.filter(contrato=contract, estado=EstadoAvisoTermino.REGISTERED).exists():
        raise ValidationError({'aviso_termino': 'El contrato vigente ya tiene un AvisoTermino registrado.'})

    aviso_fecha_efectiva = fecha_inicio - timedelta(days=1)
    if aviso_fecha_efectiva != contract.fecha_fin_vigente:
        raise ValidationError(
            {'fecha_inicio': 'El contrato nuevo debe iniciar el dia siguiente al termino vigente del contrato actual.'}
        )

    base_period = _base_period_for_replacement(contract, fecha_inicio)
    if base_period is None:
        raise ValidationError({'periodos_contractuales': 'El cambio de arrendatario requiere periodo base vigente.'})

    replacement_amount = Decimal(monto_base) if monto_base is not None else base_period.monto_base
    replacement_currency = moneda_base or base_period.moneda_base
    _validate_amount(replacement_currency, replacement_amount)

    conflict_ref = str(resolucion_conflicto_renovacion_ref or '').strip()
    conflict_reason = str(resolucion_conflicto_renovacion_motivo or '').strip()
    if bool(conflict_ref) != bool(conflict_reason):
        raise ValidationError(
            {'resolucion_conflicto_renovacion_ref': 'La resolucion guiada requiere referencia y motivo trazable.'}
        )
    if conflict_ref and not is_non_sensitive_reference(conflict_ref):
        raise ValidationError(
            {'resolucion_conflicto_renovacion_ref': 'La resolucion guiada debe usar referencia no sensible.'}
        )
    if conflict_reason and contains_sensitive_reference(conflict_reason):
        raise ValidationError(
            {'resolucion_conflicto_renovacion_motivo': 'La resolucion guiada no debe contener referencias sensibles.'}
        )

    aviso = AvisoTermino(
        contrato=contract,
        fecha_efectiva=aviso_fecha_efectiva,
        causal=str(causal_aviso or '').strip(),
        estado=EstadoAvisoTermino.REGISTERED,
        resolucion_conflicto_renovacion_ref=conflict_ref,
        resolucion_conflicto_renovacion_motivo=conflict_reason,
        registrado_por=actor_user if getattr(actor_user, 'is_authenticated', False) else None,
    )
    aviso.full_clean()
    _validate_replacement_notice_conflict(aviso=aviso, future_start=fecha_inicio)
    aviso.save()

    future_contract = Contrato(
        codigo_contrato=str(codigo_contrato or '').strip(),
        mandato_operacion=contract.mandato_operacion,
        arrendatario=arrendatario,
        fecha_inicio=fecha_inicio,
        fecha_fin_vigente=fecha_fin_vigente,
        dia_pago_mensual=dia_pago_mensual or contract.dia_pago_mensual,
        plazo_notificacion_termino_dias=(
            plazo_notificacion_termino_dias
            if plazo_notificacion_termino_dias is not None
            else contract.plazo_notificacion_termino_dias
        ),
        dias_prealerta_admin=(
            dias_prealerta_admin if dias_prealerta_admin is not None else contract.dias_prealerta_admin
        ),
        estado=EstadoContrato.FUTURE,
        identidad_envio_override=(
            identidad_envio_override if identidad_envio_override is not None else contract.identidad_envio_override
        ),
        politica_documental=politica_documental if politica_documental is not None else contract.politica_documental,
        tiene_tramos=False,
        tiene_gastos_comunes=(
            tiene_gastos_comunes if tiene_gastos_comunes is not None else contract.tiene_gastos_comunes
        ),
        snapshot_representante_legal=snapshot_representante_legal or {},
    )
    future_contract._future_contract_primary_property_id = contract.principal_property_id()
    future_contract._allow_guided_tenant_replacement = True
    future_contract.full_clean()
    future_contract.save()

    property_links = []
    for item in _contract_property_payload(contract):
        link = ContratoPropiedad(contrato=future_contract, **item)
        link.full_clean()
        link.save()
        property_links.append(link)

    replacement_period = PeriodoContractual(
        contrato=future_contract,
        numero_periodo=1,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin_vigente,
        monto_base=replacement_amount,
        moneda_base=replacement_currency,
        tipo_periodo='inicial',
        origen_periodo='cambio_arrendatario',
    )
    replacement_period.full_clean()
    replacement_period.save()

    create_audit_event(
        event_type=TENANT_REPLACEMENT_EVENT_TYPE,
        entity_type='contrato',
        entity_id=str(future_contract.pk),
        summary='Se ejecuto cambio de arrendatario mediante aviso de termino y contrato futuro.',
        actor_user=actor_user,
        ip_address=ip_address,
        metadata={
            'contrato_anterior_id': contract.pk,
            'contrato_nuevo_id': future_contract.pk,
            'aviso_termino_id': aviso.pk,
            'arrendatario_anterior_id': contract.arrendatario_id,
            'arrendatario_nuevo_id': arrendatario.pk,
            'fecha_efectiva_aviso': aviso.fecha_efectiva.isoformat(),
            'fecha_inicio_contrato_nuevo': future_contract.fecha_inicio.isoformat(),
            'fecha_fin_contrato_nuevo': future_contract.fecha_fin_vigente.isoformat(),
            'propiedades': [link.propiedad_id for link in property_links],
        },
    )

    return aviso, future_contract
