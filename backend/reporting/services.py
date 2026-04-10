from decimal import Decimal

from django.db.models import Count, Q, Sum

from audit.models import ManualResolution
from canales.models import MensajeSaliente
from cobranza.models import DistribucionCobroMensual, EstadoCuentaArrendatario, PagoMensual
from conciliacion.models import IngresoDesconocido
from contabilidad.models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    EventoContable,
    LibroDiario,
    LibroMayor,
    ObligacionTributariaMensual,
)
from contratos.models import Contrato
from patrimonio.models import ParticipacionPatrimonial, Socio, Propiedad
from sii.models import DDJJPreparacionAnual, DTEEmitido, F22PreparacionAnual, ProcesoRentaAnual


def build_operational_dashboard():
    return {
        'propiedades_activas': Propiedad.objects.filter(estado='activa').count(),
        'contratos_vigentes': Contrato.objects.filter(estado='vigente').count(),
        'contratos_futuros': Contrato.objects.filter(estado='futuro').count(),
        'pagos_pendientes': PagoMensual.objects.filter(estado_pago='pendiente').count(),
        'pagos_atrasados': PagoMensual.objects.filter(estado_pago='atrasado').count(),
        'ingresos_desconocidos_abiertos': IngresoDesconocido.objects.filter(estado='pendiente_revision').count(),
        'resoluciones_manuales_abiertas': ManualResolution.objects.filter(status='open').count(),
        'cierres_preparados': CierreMensualContable.objects.filter(estado='preparado').count(),
        'cierres_aprobados': CierreMensualContable.objects.filter(estado='aprobado').count(),
        'dtes_borrador': DTEEmitido.objects.filter(estado_dte='borrador').count(),
        'mensajes_preparados': MensajeSaliente.objects.filter(estado='preparado').count(),
        'mensajes_bloqueados': MensajeSaliente.objects.filter(estado='bloqueado').count(),
    }


def build_financial_monthly_summary(anio, mes, empresa_id=None):
    if empresa_id is None:
        payments = PagoMensual.objects.filter(anio=anio, mes=mes)
        pagos_generados = payments.count()
        facturable_total = payments.aggregate(total=Sum('monto_facturable_clp'))['total'] or Decimal('0.00')
        cobrado_total = payments.aggregate(total=Sum('monto_pagado_clp'))['total'] or Decimal('0.00')
    else:
        distributions = DistribucionCobroMensual.objects.filter(
            pago_mensual__anio=anio,
            pago_mensual__mes=mes,
            beneficiario_empresa_owner_id=empresa_id,
        )
        pagos_generados = distributions.values('pago_mensual_id').distinct().count()
        facturable_total = distributions.aggregate(total=Sum('monto_facturable_clp'))['total'] or Decimal('0.00')
        cobrado_total = distributions.aggregate(total=Sum('monto_conciliado_clp'))['total'] or Decimal('0.00')

    event_filters = Q(fecha_operativa__year=anio, fecha_operativa__month=mes, estado_contable='contabilizado')
    if empresa_id is not None:
        event_filters &= Q(empresa_id=empresa_id)
    events = EventoContable.objects.filter(event_filters)
    event_total = events.aggregate(total=Sum('monto_base'))['total'] or Decimal('0.00')

    obligations = ObligacionTributariaMensual.objects.filter(anio=anio, mes=mes)
    if empresa_id is not None:
        obligations = obligations.filter(empresa_id=empresa_id)

    closures = CierreMensualContable.objects.filter(anio=anio, mes=mes)
    if empresa_id is not None:
        closures = closures.filter(empresa_id=empresa_id)

    dtes = DTEEmitido.objects.filter(fecha_emision__year=anio, fecha_emision__month=mes)
    if empresa_id is not None:
        dtes = dtes.filter(empresa_id=empresa_id)

    return {
        'anio': anio,
        'mes': mes,
        'empresa_id': empresa_id,
        'pagos_generados': pagos_generados,
        'monto_facturable_total_clp': str(facturable_total),
        'monto_cobrado_total_clp': str(cobrado_total),
        'eventos_contables_posteados': events.count(),
        'monto_eventos_total_clp': str(event_total),
        'asientos_contables': AsientoContable.objects.filter(evento_contable__in=events).count(),
        'dtes_emitidos': dtes.count(),
        'obligaciones': [
            {
                'tipo': obligation.obligacion_tipo,
                'monto_calculado': str(obligation.monto_calculado),
                'estado_preparacion': obligation.estado_preparacion,
            }
            for obligation in obligations.order_by('obligacion_tipo')
        ],
        'cierres': [
            {
                'empresa_id': close.empresa_id,
                'estado': close.estado,
                'fecha_preparacion': close.fecha_preparacion.isoformat() if close.fecha_preparacion else None,
                'fecha_aprobacion': close.fecha_aprobacion.isoformat() if close.fecha_aprobacion else None,
            }
            for close in closures.order_by('empresa_id')
        ],
    }


def build_partner_summary(socio_id):
    socio = Socio.objects.get(pk=socio_id)
    participaciones = ParticipacionPatrimonial.objects.filter(participante_socio=socio, activo=True).select_related(
        'participante_socio',
        'participante_empresa',
        'empresa_owner',
        'comunidad_owner',
    )
    direct_properties = Propiedad.objects.filter(socio_owner=socio).order_by('codigo_propiedad')

    company_shares = [
        {
            'empresa_id': item.empresa_owner_id,
            'empresa': item.empresa_owner.razon_social,
            'porcentaje': str(item.porcentaje),
        }
        for item in participaciones
        if item.empresa_owner_id
    ]
    community_shares = [
        {
            'comunidad_id': item.comunidad_owner_id,
            'comunidad': item.comunidad_owner.nombre,
            'porcentaje': str(item.porcentaje),
        }
        for item in participaciones
        if item.comunidad_owner_id
    ]

    active_direct_contracts = Contrato.objects.filter(
        estado__in=['vigente', 'futuro'],
        contrato_propiedades__propiedad__in=direct_properties,
    ).distinct()

    state = EstadoCuentaArrendatario.objects.filter(arrendatario__contratos__mandato_operacion__propiedad__socio_owner=socio).distinct()

    return {
        'socio': {
            'id': socio.id,
            'nombre': socio.nombre,
            'rut': socio.rut,
            'email': socio.email,
        },
        'participaciones_empresas': company_shares,
        'participaciones_comunidades': community_shares,
        'propiedades_directas': [
            {
                'propiedad_id': property_item.id,
                'codigo_propiedad': property_item.codigo_propiedad,
                'direccion': property_item.direccion,
                'estado': property_item.estado,
            }
            for property_item in direct_properties
        ],
        'contratos_directos_activos': active_direct_contracts.count(),
        'estados_cuenta_relacionados': state.count(),
    }


def build_period_books_summary(empresa_id, periodo):
    libro_diario = LibroDiario.objects.filter(empresa_id=empresa_id, periodo=periodo).first()
    libro_mayor = LibroMayor.objects.filter(empresa_id=empresa_id, periodo=periodo).first()
    balance = BalanceComprobacion.objects.filter(empresa_id=empresa_id, periodo=periodo).first()

    return {
        'empresa_id': empresa_id,
        'periodo': periodo,
        'libro_diario': {
            'id': libro_diario.id if libro_diario else None,
            'estado_snapshot': libro_diario.estado_snapshot if libro_diario else None,
            'storage_ref': libro_diario.storage_ref if libro_diario else '',
            'resumen': libro_diario.resumen if libro_diario else {},
        },
        'libro_mayor': {
            'id': libro_mayor.id if libro_mayor else None,
            'estado_snapshot': libro_mayor.estado_snapshot if libro_mayor else None,
            'storage_ref': libro_mayor.storage_ref if libro_mayor else '',
            'resumen': libro_mayor.resumen if libro_mayor else {},
        },
        'balance_comprobacion': {
            'id': balance.id if balance else None,
            'estado_snapshot': balance.estado_snapshot if balance else None,
            'storage_ref': balance.storage_ref if balance else '',
            'resumen': balance.resumen if balance else {},
        },
    }


def build_annual_tax_summary(anio_tributario, empresa_id=None):
    process_queryset = ProcesoRentaAnual.objects.filter(anio_tributario=anio_tributario)
    if empresa_id is not None:
        process_queryset = process_queryset.filter(empresa_id=empresa_id)

    ddjj_queryset = DDJJPreparacionAnual.objects.filter(anio_tributario=anio_tributario)
    if empresa_id is not None:
        ddjj_queryset = ddjj_queryset.filter(empresa_id=empresa_id)

    f22_queryset = F22PreparacionAnual.objects.filter(anio_tributario=anio_tributario)
    if empresa_id is not None:
        f22_queryset = f22_queryset.filter(empresa_id=empresa_id)

    return {
        'anio_tributario': anio_tributario,
        'empresa_id': empresa_id,
        'procesos_renta': [
            {
                'empresa_id': process.empresa_id,
                'estado': process.estado,
                'fecha_preparacion': process.fecha_preparacion.isoformat() if process.fecha_preparacion else None,
                'resumen_anual': process.resumen_anual,
            }
            for process in process_queryset.order_by('empresa_id')
        ],
        'ddjj_preparadas': [
            {
                'empresa_id': item.empresa_id,
                'estado_preparacion': item.estado_preparacion,
                'paquete_ref': item.paquete_ref,
                'resumen_paquete': item.resumen_paquete,
            }
            for item in ddjj_queryset.order_by('empresa_id')
        ],
        'f22_preparados': [
            {
                'empresa_id': item.empresa_id,
                'estado_preparacion': item.estado_preparacion,
                'borrador_ref': item.borrador_ref,
                'resumen_f22': item.resumen_f22,
            }
            for item in f22_queryset.order_by('empresa_id')
        ],
    }


def build_migration_manual_resolution_summary(status='open'):
    resolutions = ManualResolution.objects.filter(category__startswith='migration.')
    if status:
        resolutions = resolutions.filter(status=status)

    by_category = resolutions.values('category').annotate(total=Count('id')).order_by('category')
    by_scope_type = resolutions.values('scope_type').annotate(total=Count('id')).order_by('scope_type')

    owner_manual_required = resolutions.filter(category='migration.propiedad.owner_manual_required').order_by('created_at')

    return {
        'status': status,
        'total': resolutions.count(),
        'categorias': [
            {'category': item['category'], 'total': item['total']}
            for item in by_category
        ],
        'scope_types': [
            {'scope_type': item['scope_type'], 'total': item['total']}
            for item in by_scope_type
        ],
        'propiedades_owner_manual_required': [
            {
                'id': str(item.id),
                'scope_reference': item.scope_reference,
                'summary': item.summary,
                'codigo': item.metadata.get('codigo'),
                'direccion': item.metadata.get('direccion'),
                'candidate_owner_model': item.metadata.get('candidate_owner_model'),
                'participaciones_count': item.metadata.get('participaciones_count'),
                'total_pct': item.metadata.get('total_pct'),
                'blocked_contract_legacy_ids': item.metadata.get('blocked_contract_legacy_ids', []),
                'socios': item.metadata.get('socios', []),
            }
            for item in owner_manual_required
        ],
    }
