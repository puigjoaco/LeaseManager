from django.db import transaction
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from audit.services import create_audit_event

from .models import Arrendatario, AvisoTermino, CodeudorSolidario, Contrato, ContratoPropiedad, PeriodoContractual
from .serializers import (
    ArrendatarioSerializer,
    AvisoTerminoSerializer,
    CodeudorSolidarioReadSerializer,
    ContratoPropiedadReadSerializer,
    ContratoSerializer,
    PeriodoContractualReadSerializer,
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


class ArrendatarioListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ArrendatarioSerializer
    queryset = Arrendatario.objects.all()
    audit_entity_type = 'arrendatario'
    audit_entity_label = 'arrendatario'


class ArrendatarioDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ArrendatarioSerializer
    queryset = Arrendatario.objects.all()
    audit_entity_type = 'arrendatario'
    audit_entity_label = 'arrendatario'


class ContratoListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ContratoSerializer
    queryset = Contrato.objects.select_related('mandato_operacion', 'arrendatario').prefetch_related(
        'contrato_propiedades__propiedad',
        'periodos_contractuales',
        'codeudores_solidarios',
    )
    audit_entity_type = 'contrato'
    audit_entity_label = 'contrato'


class ContratoDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ContratoSerializer
    queryset = Contrato.objects.select_related('mandato_operacion', 'arrendatario').prefetch_related(
        'contrato_propiedades__propiedad',
        'periodos_contractuales',
        'codeudores_solidarios',
    )
    audit_entity_type = 'contrato'
    audit_entity_label = 'contrato'


class AvisoTerminoListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AvisoTerminoSerializer
    queryset = AvisoTermino.objects.select_related('contrato', 'registrado_por').all()
    audit_entity_type = 'aviso_termino'
    audit_entity_label = 'aviso de termino'


class AvisoTerminoDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AvisoTerminoSerializer
    queryset = AvisoTermino.objects.select_related('contrato', 'registrado_por').all()
    audit_entity_type = 'aviso_termino'
    audit_entity_label = 'aviso de termino'


class ContratoPropiedadListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ContratoPropiedadReadSerializer
    queryset = ContratoPropiedad.objects.select_related('contrato', 'propiedad').all()


class ContratoPropiedadDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ContratoPropiedadReadSerializer
    queryset = ContratoPropiedad.objects.select_related('contrato', 'propiedad').all()


class PeriodoContractualListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PeriodoContractualReadSerializer
    queryset = PeriodoContractual.objects.select_related('contrato').all()


class PeriodoContractualDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PeriodoContractualReadSerializer
    queryset = PeriodoContractual.objects.select_related('contrato').all()


class CodeudorSolidarioListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CodeudorSolidarioReadSerializer
    queryset = CodeudorSolidario.objects.select_related('contrato').all()


class CodeudorSolidarioDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CodeudorSolidarioReadSerializer
    queryset = CodeudorSolidario.objects.select_related('contrato').all()

