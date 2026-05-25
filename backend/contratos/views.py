from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import ManualResolution
from audit.services import create_audit_event
from core.permissions import OperationalModulePermission
from core.reference_validation import redact_sensitive_reference
from core.scope_access import ScopedQuerysetMixin, get_scope_access, scope_queryset_for_access
from operacion.models import MandatoOperacion

from .models import (
    Arrendatario,
    AvisoTermino,
    CodeudorSolidario,
    ContactoPagoArrendatario,
    Contrato,
    ContratoPropiedad,
    EARLY_TERMINATION_PARTIAL_MONTH_EVENT_TYPE,
    PeriodoContractual,
    WHATSAPP_BLOCK_ALERT_CATEGORY,
    WHATSAPP_BLOCK_EVENT_TYPE,
    WHATSAPP_REHABILITATION_EVENT_TYPE,
)
from .serializers import (
    ArrendatarioSerializer,
    ArrendatarioWhatsappBlockSerializer,
    ArrendatarioWhatsappRehabilitateSerializer,
    AvisoTerminoSerializer,
    CodeudorSolidarioReadSerializer,
    ContactoPagoArrendatarioSerializer,
    ContratoPropiedadReadSerializer,
    ContratoSerializer,
    PeriodoContractualReadSerializer,
    raise_drf_validation_error,
)


class AuditCreateUpdateMixin:
    audit_entity_type = ''
    audit_entity_label = ''

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
        self._create_audit_event(instance=instance, action='created')

    def perform_update(self, serializer):
        previous_state = self._extract_state(serializer.instance)
        with transaction.atomic():
            instance = serializer.save()
        self._create_audit_event(instance=instance, action='updated')
        if previous_state != self._extract_state(instance):
            self._create_audit_event(
                instance=instance,
                action='state_changed',
                summary=f'Se cambio el estado de {self.audit_entity_label} {instance.pk}',
            )

    def _extract_state(self, instance):
        for field in ('estado_contacto', 'estado'):
            if hasattr(instance, field):
                return getattr(instance, field)
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'contratos.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


def create_whatsapp_block_trace(*, tenant, request):
    ManualResolution.objects.create(
        category=WHATSAPP_BLOCK_ALERT_CATEGORY,
        scope_type='arrendatario',
        scope_reference=str(tenant.pk),
        summary='Bloqueo definitivo de WhatsApp requiere seguimiento administrativo.',
        rationale=tenant.whatsapp_bloqueo_motivo,
        requested_by=request.user,
        metadata={
            'arrendatario_id': tenant.pk,
            'evidencia_ref': tenant.whatsapp_bloqueo_evidencia_ref,
            'whatsapp_bloqueado_at': tenant.whatsapp_bloqueado_at.isoformat() if tenant.whatsapp_bloqueado_at else '',
        },
    )
    create_audit_event(
        event_type=WHATSAPP_BLOCK_EVENT_TYPE,
        severity='warning',
        entity_type='arrendatario',
        entity_id=str(tenant.pk),
        summary='Se registro bloqueo definitivo de WhatsApp para el arrendatario.',
        actor_user=request.user,
        ip_address=request.META.get('REMOTE_ADDR'),
        metadata={
            'arrendatario_id': tenant.pk,
            'evidencia_ref': tenant.whatsapp_bloqueo_evidencia_ref,
            'whatsapp_bloqueado_at': tenant.whatsapp_bloqueado_at.isoformat() if tenant.whatsapp_bloqueado_at else '',
        },
    )


def resolve_whatsapp_block_alerts(*, tenant, request, rehabilitacion_ref: str):
    open_alerts = list(ManualResolution.objects.filter(
        category=WHATSAPP_BLOCK_ALERT_CATEGORY,
        scope_type='arrendatario',
        scope_reference=str(tenant.pk),
        status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW],
    ))
    resolved_at = timezone.now()
    for alert in open_alerts:
        alert.status = ManualResolution.Status.RESOLVED
        alert.resolved_at = resolved_at
        alert.resolved_by = request.user
        metadata = alert.metadata if isinstance(alert.metadata, dict) else {}
        alert.metadata = {
            **metadata,
            'rehabilitacion_ref': rehabilitacion_ref,
            'whatsapp_rehabilitado_at': tenant.whatsapp_rehabilitado_at.isoformat()
            if tenant.whatsapp_rehabilitado_at
            else '',
        }
        alert.save(update_fields=['status', 'resolved_at', 'resolved_by', 'metadata'])
    create_audit_event(
        event_type=WHATSAPP_REHABILITATION_EVENT_TYPE,
        entity_type='arrendatario',
        entity_id=str(tenant.pk),
        summary='Se registro rehabilitacion manual de WhatsApp para el arrendatario.',
        actor_user=request.user,
        ip_address=request.META.get('REMOTE_ADDR'),
        metadata={
            'arrendatario_id': tenant.pk,
            'rehabilitacion_ref': rehabilitacion_ref,
            'whatsapp_rehabilitado_at': tenant.whatsapp_rehabilitado_at.isoformat()
            if tenant.whatsapp_rehabilitado_at
            else '',
            'alertas_resueltas': len(open_alerts),
        },
    )


def contract_proration_trace_key(contract):
    return (
        contract.estado,
        contract.fecha_fin_vigente,
        (contract.terminacion_anticipada_prorrata_ref or '').strip(),
        (contract.terminacion_anticipada_prorrata_motivo or '').strip(),
    )


def create_early_termination_proration_trace(*, contract, request):
    create_audit_event(
        event_type=EARLY_TERMINATION_PARTIAL_MONTH_EVENT_TYPE,
        severity='warning',
        entity_type='contrato',
        entity_id=str(contract.pk),
        summary='Se registro decision auditada para ultimo mes parcial por terminacion anticipada.',
        actor_user=request.user,
        ip_address=request.META.get('REMOTE_ADDR'),
        metadata={
            'codigo_contrato': contract.codigo_contrato,
            'fecha_fin_vigente': contract.fecha_fin_vigente.isoformat(),
            'terminacion_anticipada_prorrata_ref': contract.terminacion_anticipada_prorrata_ref,
            'terminacion_anticipada_prorrata_motivo': contract.terminacion_anticipada_prorrata_motivo,
        },
    )


class ContractsSnapshotView(APIView):
    permission_classes = [OperationalModulePermission]

    def get(self, request):
        access = get_scope_access(request.user)
        arrendatarios = scope_queryset_for_access(
            Arrendatario.objects.prefetch_related('contactos_pago').order_by('nombre_razon_social', 'id'),
            access,
            property_paths=('contratos__mandato_operacion__propiedad_id',),
        )
        mandatos = scope_queryset_for_access(
            MandatoOperacion.objects.select_related(
                'propiedad',
                'propietario_empresa_owner',
                'propietario_comunidad_owner',
                'propietario_socio_owner',
            ).order_by('id'),
            access,
            property_paths=('propiedad_id',),
            bank_account_paths=('cuenta_recaudadora_id',),
        )
        contratos = scope_queryset_for_access(
            Contrato.objects.select_related(
                'mandato_operacion__propiedad',
                'arrendatario',
                'identidad_envio_override',
                'politica_documental',
            ).prefetch_related(
                'contrato_propiedades__propiedad',
                'periodos_contractuales',
            ).order_by('codigo_contrato', 'id'),
            access,
            property_paths=('mandato_operacion__propiedad_id',),
        )
        avisos = scope_queryset_for_access(
            AvisoTermino.objects.select_related('contrato').order_by('-fecha_efectiva', '-id'),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        )

        return Response(
            {
                'arrendatarios': [
                    {
                        'id': item.id,
                        'nombre_razon_social': item.nombre_razon_social,
                        'rut': item.rut,
                        'tipo_arrendatario': item.tipo_arrendatario,
                        'email': item.email or '',
                        'telefono': item.telefono or '',
                        'domicilio_notificaciones': item.domicilio_notificaciones or '',
                        'estado_contacto': item.estado_contacto,
                        'nacionalidad': item.nacionalidad or '',
                        'estado_civil': item.estado_civil or '',
                        'profesion': item.profesion or '',
                        'whatsapp_opt_in': item.whatsapp_opt_in,
                        'whatsapp_opt_in_evidencia_ref': redact_sensitive_reference(
                            item.whatsapp_opt_in_evidencia_ref
                        ),
                        'whatsapp_bloqueado': item.whatsapp_bloqueado,
                        'whatsapp_bloqueo_motivo': item.whatsapp_bloqueo_motivo or '',
                        'whatsapp_bloqueo_evidencia_ref': redact_sensitive_reference(
                            item.whatsapp_bloqueo_evidencia_ref
                        ),
                        'whatsapp_bloqueado_at': item.whatsapp_bloqueado_at,
                        'whatsapp_rehabilitacion_ref': redact_sensitive_reference(
                            item.whatsapp_rehabilitacion_ref
                        ),
                        'whatsapp_rehabilitado_at': item.whatsapp_rehabilitado_at,
                        'contactos_pago': [
                            {
                                'id': contact.id,
                                'nombre': contact.nombre,
                                'rol_operativo': contact.rol_operativo,
                                'email': contact.email or '',
                                'telefono': contact.telefono or '',
                                'evidencia_autorizacion_ref': redact_sensitive_reference(
                                    contact.evidencia_autorizacion_ref
                                ),
                                'es_principal': contact.es_principal,
                                'estado': contact.estado,
                            }
                            for contact in item.contactos_pago.all()
                        ],
                    }
                    for item in arrendatarios
                ],
                'mandatos': [
                    {
                        'id': item.id,
                        'propiedad_codigo': item.propiedad.codigo_propiedad,
                        'propietario_display': (
                            item.propietario_empresa_owner.razon_social if item.propietario_empresa_owner_id
                            else item.propietario_comunidad_owner.nombre if item.propietario_comunidad_owner_id
                            else item.propietario_socio_owner.nombre
                        ),
                    }
                    for item in mandatos
                ],
                'contratos': [
                    {
                        'id': item.id,
                        'codigo_contrato': item.codigo_contrato,
                        'mandato_operacion': item.mandato_operacion_id,
                        'arrendatario': item.arrendatario_id,
                        'fecha_inicio': item.fecha_inicio,
                        'fecha_fin_vigente': item.fecha_fin_vigente,
                        'fecha_entrega': item.fecha_entrega,
                        'fecha_registro_operativo': item.fecha_registro_operativo,
                        'terminacion_anticipada_prorrata_ref': redact_sensitive_reference(
                            item.terminacion_anticipada_prorrata_ref
                        ),
                        'terminacion_anticipada_prorrata_motivo': (
                            item.terminacion_anticipada_prorrata_motivo or ''
                        ),
                        'requiere_notificacion_manual_retroactiva': (
                            item.requires_retroactive_manual_notification()
                        ),
                        'alerta_notificacion_manual_retroactiva': (
                            item.retroactive_manual_notification_alert()
                        ),
                        'dia_pago_mensual': item.dia_pago_mensual,
                        'plazo_notificacion_termino_dias': item.plazo_notificacion_termino_dias,
                        'dias_prealerta_admin': item.dias_prealerta_admin,
                        'estado': item.estado,
                        'identidad_envio_override': item.identidad_envio_override_id,
                        'identidad_envio_override_display': (
                            item.identidad_envio_override.remitente_visible
                            if item.identidad_envio_override_id
                            else None
                        ),
                        'politica_documental': item.politica_documental_id,
                        'politica_documental_tipo': (
                            item.politica_documental.tipo_documental
                            if item.politica_documental_id
                            else None
                        ),
                        'politica_documental_estado': (
                            item.politica_documental.estado
                            if item.politica_documental_id
                            else None
                        ),
                        'tiene_tramos': item.tiene_tramos,
                        'tiene_gastos_comunes': item.tiene_gastos_comunes,
                        'contrato_propiedades_detail': [
                            {
                                'propiedad': prop.propiedad_id,
                                'propiedad_codigo': prop.propiedad.codigo_propiedad,
                                'propiedad_direccion': prop.propiedad.direccion,
                                'rol_en_contrato': prop.rol_en_contrato,
                            }
                            for prop in item.contrato_propiedades.all()
                        ],
                        'periodos_contractuales_detail': [
                            {
                                'numero_periodo': periodo.numero_periodo,
                                'fecha_inicio': periodo.fecha_inicio,
                                'fecha_fin': periodo.fecha_fin,
                                'monto_base': periodo.monto_base,
                                'moneda_base': periodo.moneda_base,
                                'tipo_periodo': periodo.tipo_periodo,
                                'origen_periodo': periodo.origen_periodo,
                            }
                            for periodo in item.periodos_contractuales.all()
                        ],
                    }
                    for item in contratos
                ],
                'avisos': [
                    {
                        'id': item.id,
                        'contrato': item.contrato_id,
                        'fecha_efectiva': item.fecha_efectiva,
                        'causal': item.causal,
                        'estado': item.estado,
                        'fecha_limite_registro_oportuno': item.latest_timely_registration_at(),
                        'registrado_fuera_plazo': item.is_late_registered_notice(),
                        'alerta_registro_fuera_plazo': item.late_registration_alert(),
                    }
                    for item in avisos
                ],
            }
        )


class ArrendatarioListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ArrendatarioSerializer
    queryset = Arrendatario.objects.all()
    property_scope_paths = ('contratos__mandato_operacion__propiedad_id',)
    audit_entity_type = 'arrendatario'
    audit_entity_label = 'arrendatario'

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            if instance.whatsapp_bloqueado:
                create_whatsapp_block_trace(tenant=instance, request=self.request)
        self._create_audit_event(instance=instance, action='created')


class ArrendatarioDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ArrendatarioSerializer
    queryset = Arrendatario.objects.all()
    property_scope_paths = ('contratos__mandato_operacion__propiedad_id',)
    audit_entity_type = 'arrendatario'
    audit_entity_label = 'arrendatario'

    def perform_update(self, serializer):
        was_blocked = bool(serializer.instance.whatsapp_bloqueado)
        previous_state = self._extract_state(serializer.instance)
        with transaction.atomic():
            instance = serializer.save()
            if instance.whatsapp_bloqueado and not was_blocked:
                create_whatsapp_block_trace(tenant=instance, request=self.request)
            if was_blocked and not instance.whatsapp_bloqueado:
                if not instance.whatsapp_rehabilitacion_ref.strip():
                    raise DRFValidationError(
                        {'whatsapp_rehabilitacion_ref': 'La rehabilitacion manual requiere referencia trazable.'}
                    )
                if instance.whatsapp_rehabilitado_at is None:
                    instance.whatsapp_rehabilitado_at = timezone.now()
                    instance.save(update_fields=['whatsapp_rehabilitado_at', 'updated_at'])
                resolve_whatsapp_block_alerts(
                    tenant=instance,
                    request=self.request,
                    rehabilitacion_ref=instance.whatsapp_rehabilitacion_ref,
                )
        self._create_audit_event(instance=instance, action='updated')
        if previous_state != self._extract_state(instance):
            self._create_audit_event(
                instance=instance,
                action='state_changed',
                summary=f'Se cambio el estado de {self.audit_entity_label} {instance.pk}',
            )


class ArrendatarioWhatsappBlockView(ScopedQuerysetMixin, generics.GenericAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ArrendatarioWhatsappBlockSerializer
    queryset = Arrendatario.objects.all()
    property_scope_paths = ('contratos__mandato_operacion__propiedad_id',)

    def post(self, request, pk):
        tenant = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        with transaction.atomic():
            try:
                tenant.block_whatsapp(
                    motivo=payload['motivo'],
                    evidencia_ref=payload['evidencia_ref'],
                )
            except DjangoValidationError as error:
                raise_drf_validation_error(error)
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
            create_whatsapp_block_trace(tenant=tenant, request=request)

        return Response(ArrendatarioSerializer(tenant, context={'request': request}).data)


class ArrendatarioWhatsappRehabilitateView(ScopedQuerysetMixin, generics.GenericAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ArrendatarioWhatsappRehabilitateSerializer
    queryset = Arrendatario.objects.all()
    property_scope_paths = ('contratos__mandato_operacion__propiedad_id',)

    def post(self, request, pk):
        tenant = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        with transaction.atomic():
            try:
                tenant.rehabilitate_whatsapp(rehabilitacion_ref=payload['rehabilitacion_ref'])
            except DjangoValidationError as error:
                raise_drf_validation_error(error)
            tenant.save(
                update_fields=[
                    'whatsapp_bloqueado',
                    'whatsapp_rehabilitacion_ref',
                    'whatsapp_rehabilitado_at',
                    'updated_at',
                ]
            )
            resolve_whatsapp_block_alerts(
                tenant=tenant,
                request=request,
                rehabilitacion_ref=payload['rehabilitacion_ref'],
            )

        return Response(ArrendatarioSerializer(tenant, context={'request': request}).data)


class ContactoPagoArrendatarioListCreateView(
    ScopedQuerysetMixin,
    AuditCreateUpdateMixin,
    generics.ListCreateAPIView,
):
    permission_classes = [OperationalModulePermission]
    serializer_class = ContactoPagoArrendatarioSerializer
    queryset = ContactoPagoArrendatario.objects.select_related('arrendatario').all()
    property_scope_paths = ('arrendatario__contratos__mandato_operacion__propiedad_id',)
    audit_entity_type = 'contacto_pago_arrendatario'
    audit_entity_label = 'contacto de pago'


class ContactoPagoArrendatarioDetailView(
    ScopedQuerysetMixin,
    AuditCreateUpdateMixin,
    generics.RetrieveUpdateAPIView,
):
    permission_classes = [OperationalModulePermission]
    serializer_class = ContactoPagoArrendatarioSerializer
    queryset = ContactoPagoArrendatario.objects.select_related('arrendatario').all()
    property_scope_paths = ('arrendatario__contratos__mandato_operacion__propiedad_id',)
    audit_entity_type = 'contacto_pago_arrendatario'
    audit_entity_label = 'contacto de pago'


class ContratoListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ContratoSerializer
    queryset = Contrato.objects.select_related(
        'mandato_operacion',
        'arrendatario',
        'identidad_envio_override',
        'politica_documental',
    ).prefetch_related(
        'contrato_propiedades__propiedad',
        'periodos_contractuales',
        'codeudores_solidarios',
    )
    property_scope_paths = ('mandato_operacion__propiedad_id',)
    audit_entity_type = 'contrato'
    audit_entity_label = 'contrato'

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
        self._create_audit_event(instance=instance, action='created')
        if instance.requires_retroactive_manual_notification():
            create_audit_event(
                event_type='contratos.contrato.retroactive_manual_notification_alert',
                entity_type='contrato',
                entity_id=str(instance.pk),
                summary='Contrato retroactivo requiere revisar posible notificacion manual.',
                actor_user=self.request.user,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                metadata={
                    'codigo_contrato': instance.codigo_contrato,
                    'fecha_inicio': instance.fecha_inicio.isoformat(),
                    'fecha_registro_operativo': (
                        instance.fecha_registro_operativo.isoformat()
                        if instance.fecha_registro_operativo
                        else ''
                    ),
                    'dia_corte': 5,
                },
            )
        if instance.has_partial_early_termination_month():
            create_early_termination_proration_trace(contract=instance, request=self.request)


class ContratoDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ContratoSerializer
    queryset = Contrato.objects.select_related(
        'mandato_operacion',
        'arrendatario',
        'identidad_envio_override',
        'politica_documental',
    ).prefetch_related(
        'contrato_propiedades__propiedad',
        'periodos_contractuales',
        'codeudores_solidarios',
    )
    property_scope_paths = ('mandato_operacion__propiedad_id',)
    audit_entity_type = 'contrato'
    audit_entity_label = 'contrato'

    def perform_update(self, serializer):
        previous_state = self._extract_state(serializer.instance)
        previous_proration_trace = contract_proration_trace_key(serializer.instance)
        with transaction.atomic():
            instance = serializer.save()
        self._create_audit_event(instance=instance, action='updated')
        if previous_state != self._extract_state(instance):
            self._create_audit_event(
                instance=instance,
                action='state_changed',
                summary=f'Se cambio el estado de {self.audit_entity_label} {instance.pk}',
            )
        if (
            instance.has_partial_early_termination_month()
            and contract_proration_trace_key(instance) != previous_proration_trace
        ):
            create_early_termination_proration_trace(contract=instance, request=self.request)


class AvisoTerminoListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = AvisoTerminoSerializer
    queryset = AvisoTermino.objects.select_related('contrato', 'registrado_por').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
    audit_entity_type = 'aviso_termino'
    audit_entity_label = 'aviso de termino'


class AvisoTerminoDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = AvisoTerminoSerializer
    queryset = AvisoTermino.objects.select_related('contrato', 'registrado_por').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
    audit_entity_type = 'aviso_termino'
    audit_entity_label = 'aviso de termino'


class ContratoPropiedadListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ContratoPropiedadReadSerializer
    queryset = ContratoPropiedad.objects.select_related('contrato', 'propiedad').all()
    property_scope_paths = ('propiedad_id',)


class ContratoPropiedadDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ContratoPropiedadReadSerializer
    queryset = ContratoPropiedad.objects.select_related('contrato', 'propiedad').all()
    property_scope_paths = ('propiedad_id',)


class PeriodoContractualListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = PeriodoContractualReadSerializer
    queryset = PeriodoContractual.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)


class PeriodoContractualDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = PeriodoContractualReadSerializer
    queryset = PeriodoContractual.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)


class CodeudorSolidarioListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CodeudorSolidarioReadSerializer
    queryset = CodeudorSolidario.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)


class CodeudorSolidarioDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CodeudorSolidarioReadSerializer
    queryset = CodeudorSolidario.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
