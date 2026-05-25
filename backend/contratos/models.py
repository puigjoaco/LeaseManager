import calendar
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.reference_validation import is_non_sensitive_reference
from documentos.models import EstadoPoliticaFirma, PoliticaFirmaYNotaria, TipoDocumental
from operacion.models import EstadoIdentidadEnvio, IdentidadDeEnvio, MandatoOperacion
from patrimonio.validators import normalize_rut, validate_rut


codigo_efectivo_validator = RegexValidator(
    regex=r'^\d{3}$',
    message='El codigo de conciliacion efectivo debe tener exactamente 3 digitos.',
)
RETROACTIVE_MANUAL_NOTIFICATION_CUTOFF_DAY = 5
NOTICE_DEADLINE_END_OF_DAY = time(23, 59, 59)
RENEWAL_PERIOD_KIND = 'renovacion'
INTERNATIONAL_PHONE_RE = re.compile(r'^\+[1-9]\d{7,14}$')
WHATSAPP_BLOCK_ALERT_CATEGORY = 'canales.whatsapp.bloqueo_definitivo'
WHATSAPP_BLOCK_EVENT_TYPE = 'contratos.arrendatario.whatsapp_blocked'
WHATSAPP_REHABILITATION_EVENT_TYPE = 'contratos.arrendatario.whatsapp_rehabilitated'
EARLY_TERMINATION_PARTIAL_MONTH_EVENT_TYPE = 'contratos.contrato.early_termination_partial_month_decision'


def is_international_phone_number(value):
    return bool(INTERNATIONAL_PHONE_RE.fullmatch(str(value or '').strip()))


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TipoArrendatario(models.TextChoices):
    NATURAL = 'persona_natural', 'Persona natural'
    COMPANY = 'empresa', 'Empresa'


class EstadoContactoArrendatario(models.TextChoices):
    PENDING = 'pendiente', 'Pendiente'
    ACTIVE = 'activo', 'Activo'
    INACTIVE = 'inactivo', 'Inactivo'


class EstadoCivilArrendatario(models.TextChoices):
    SINGLE = 'soltero', 'Soltero'
    MARRIED = 'casado', 'Casado'
    DIVORCED = 'divorciado', 'Divorciado'
    WIDOWED = 'viudo', 'Viudo'
    CIVIL_UNION = 'conviviente_civil', 'Conviviente civil'
    OTHER = 'otro', 'Otro'


class EstadoContactoPago(models.TextChoices):
    ACTIVE = 'activo', 'Activo'
    INACTIVE = 'inactivo', 'Inactivo'


class EstadoContrato(models.TextChoices):
    PENDING = 'pendiente_activacion', 'Pendiente activacion'
    FUTURE = 'futuro', 'Futuro'
    ACTIVE = 'vigente', 'Vigente'
    EARLY_TERMINATED = 'terminado_anticipadamente', 'Terminado anticipadamente'
    FINISHED = 'finalizado', 'Finalizado'
    CANCELED = 'cancelado', 'Cancelado'


class RolContratoPropiedad(models.TextChoices):
    PRIMARY = 'principal', 'Principal'
    LINKED = 'vinculada', 'Vinculada'


class EstadoCodeudorSolidario(models.TextChoices):
    ACTIVE = 'activo', 'Activo'
    INACTIVE = 'inactivo', 'Inactivo'


class EstadoAvisoTermino(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    REGISTERED = 'registrado', 'Registrado'
    CANCELED = 'cancelado', 'Cancelado'


class MonedaBaseContrato(models.TextChoices):
    CLP = 'CLP', 'CLP'
    UF = 'UF', 'UF'


def normalize_representante_legal_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        raise ValidationError(
            {'snapshot_representante_legal': 'El snapshot de representante legal debe ser un objeto con nombre y RUT.'}
        )

    nombre = str(snapshot.get('nombre') or '').strip()
    rut_value = str(snapshot.get('rut') or '').strip()
    if not nombre or not rut_value:
        raise ValidationError(
            {'snapshot_representante_legal': 'El snapshot de representante legal debe incluir nombre y RUT.'}
        )

    try:
        normalized_rut = validate_rut(rut_value)
    except ValidationError as error:
        raise ValidationError({'snapshot_representante_legal': error.messages}) from error

    normalized = dict(snapshot)
    normalized['nombre'] = nombre
    normalized['rut'] = normalized_rut
    return normalized


class Arrendatario(TimestampedModel):
    tipo_arrendatario = models.CharField(max_length=20, choices=TipoArrendatario.choices)
    nombre_razon_social = models.CharField(max_length=255)
    rut = models.CharField(max_length=16, unique=True, validators=[validate_rut])
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    domicilio_notificaciones = models.CharField(max_length=255, blank=True)
    estado_contacto = models.CharField(
        max_length=16,
        choices=EstadoContactoArrendatario.choices,
        default=EstadoContactoArrendatario.PENDING,
    )
    nacionalidad = models.CharField(max_length=64, blank=True)
    estado_civil = models.CharField(max_length=32, choices=EstadoCivilArrendatario.choices, blank=True)
    profesion = models.CharField(max_length=128, blank=True)
    whatsapp_opt_in = models.BooleanField(default=False)
    whatsapp_opt_in_evidencia_ref = models.CharField(max_length=255, blank=True)
    whatsapp_bloqueado = models.BooleanField(default=False)
    whatsapp_bloqueo_motivo = models.TextField(blank=True)
    whatsapp_bloqueo_evidencia_ref = models.CharField(max_length=255, blank=True)
    whatsapp_bloqueado_at = models.DateTimeField(null=True, blank=True)
    whatsapp_rehabilitacion_ref = models.CharField(max_length=255, blank=True)
    whatsapp_rehabilitado_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['nombre_razon_social']

    def __str__(self):
        return self.nombre_razon_social

    def save(self, *args, **kwargs):
        self.rut = normalize_rut(self.rut)
        if self.whatsapp_bloqueado and self.whatsapp_bloqueado_at is None:
            self.whatsapp_bloqueado_at = timezone.now()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self.nacionalidad = (self.nacionalidad or '').strip()
        self.profesion = (self.profesion or '').strip()
        if self.whatsapp_bloqueado:
            if self.whatsapp_opt_in:
                raise ValidationError({'whatsapp_opt_in': 'No puede existir opt-in activo si WhatsApp esta bloqueado.'})
            if not self.whatsapp_bloqueo_motivo.strip():
                raise ValidationError(
                    {'whatsapp_bloqueo_motivo': 'El bloqueo definitivo de WhatsApp requiere motivo trazable.'}
                )
            if not self.whatsapp_bloqueo_evidencia_ref.strip():
                raise ValidationError(
                    {
                        'whatsapp_bloqueo_evidencia_ref': (
                            'El bloqueo definitivo de WhatsApp requiere evidencia no sensible.'
                        )
                    }
                )
            if not is_non_sensitive_reference(self.whatsapp_bloqueo_evidencia_ref):
                raise ValidationError(
                    {
                        'whatsapp_bloqueo_evidencia_ref': (
                            'La evidencia de bloqueo WhatsApp debe ser una referencia no sensible.'
                        )
                    }
                )
        if self.whatsapp_rehabilitacion_ref.strip() and not is_non_sensitive_reference(
            self.whatsapp_rehabilitacion_ref
        ):
            raise ValidationError(
                {
                    'whatsapp_rehabilitacion_ref': (
                        'La rehabilitacion manual de WhatsApp debe usar una referencia no sensible.'
                    )
                }
            )
        if not self.whatsapp_opt_in:
            return
        if not self.telefono:
            raise ValidationError({'telefono': 'El opt-in de WhatsApp requiere telefono operativo.'})
        if not is_international_phone_number(self.telefono):
            raise ValidationError(
                {'telefono': 'El opt-in de WhatsApp requiere telefono en formato internacional + y digitos.'}
            )
        if not self.whatsapp_opt_in_evidencia_ref.strip():
            raise ValidationError(
                {
                    'whatsapp_opt_in_evidencia_ref': (
                        'El opt-in de WhatsApp requiere referencia de evidencia.'
                    )
                }
            )
        if not is_non_sensitive_reference(self.whatsapp_opt_in_evidencia_ref):
            raise ValidationError(
                {
                    'whatsapp_opt_in_evidencia_ref': (
                        'La evidencia de opt-in WhatsApp debe ser una referencia no sensible.'
                    )
                }
            )

    def block_whatsapp(self, *, motivo: str, evidencia_ref: str):
        self.whatsapp_bloqueado = True
        self.whatsapp_opt_in = False
        self.whatsapp_bloqueo_motivo = str(motivo or '').strip()
        self.whatsapp_bloqueo_evidencia_ref = str(evidencia_ref or '').strip()
        self.whatsapp_bloqueado_at = timezone.now()
        self.whatsapp_rehabilitacion_ref = ''
        self.whatsapp_rehabilitado_at = None
        self.full_clean()

    def rehabilitate_whatsapp(self, *, rehabilitacion_ref: str):
        if not self.whatsapp_bloqueado:
            raise ValidationError({'whatsapp_bloqueado': 'El contacto no tiene WhatsApp bloqueado.'})
        self.whatsapp_bloqueado = False
        self.whatsapp_rehabilitacion_ref = str(rehabilitacion_ref or '').strip()
        self.whatsapp_rehabilitado_at = timezone.now()
        self.full_clean()


class ContactoPagoArrendatario(TimestampedModel):
    arrendatario = models.ForeignKey(
        Arrendatario,
        on_delete=models.CASCADE,
        related_name='contactos_pago',
    )
    nombre = models.CharField(max_length=255)
    rol_operativo = models.CharField(max_length=64, default='contacto_pago')
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    evidencia_autorizacion_ref = models.CharField(max_length=255, blank=True)
    es_principal = models.BooleanField(default=False)
    estado = models.CharField(
        max_length=16,
        choices=EstadoContactoPago.choices,
        default=EstadoContactoPago.ACTIVE,
    )

    class Meta:
        ordering = ['arrendatario_id', '-es_principal', 'nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['arrendatario'],
                condition=Q(es_principal=True, estado=EstadoContactoPago.ACTIVE),
                name='uniq_contacto_pago_principal_activo_por_arrendatario',
            ),
        ]

    def __str__(self):
        return f'{self.arrendatario.nombre_razon_social} - {self.nombre}'

    def clean(self):
        super().clean()
        if self.estado == EstadoContactoPago.ACTIVE:
            if not self.nombre.strip():
                raise ValidationError({'nombre': 'El contacto de pago activo requiere nombre.'})
            if not ((self.email or '').strip() or (self.telefono or '').strip()):
                raise ValidationError(
                    {'email': 'El contacto de pago activo requiere email o telefono estructurado.'}
                )
        if self.evidencia_autorizacion_ref.strip() and not is_non_sensitive_reference(
            self.evidencia_autorizacion_ref
        ):
            raise ValidationError(
                {
                    'evidencia_autorizacion_ref': (
                        'La evidencia del contacto de pago debe ser una referencia no sensible.'
                    )
                }
            )


class Contrato(TimestampedModel):
    codigo_contrato = models.CharField(max_length=64, unique=True)
    mandato_operacion = models.ForeignKey(
        MandatoOperacion,
        on_delete=models.PROTECT,
        related_name='contratos',
    )
    arrendatario = models.ForeignKey(
        Arrendatario,
        on_delete=models.PROTECT,
        related_name='contratos',
    )
    fecha_inicio = models.DateField()
    fecha_fin_vigente = models.DateField()
    fecha_entrega = models.DateField(null=True, blank=True)
    fecha_registro_operativo = models.DateField(null=True, blank=True)
    terminacion_anticipada_prorrata_ref = models.CharField(max_length=255, blank=True)
    terminacion_anticipada_prorrata_motivo = models.TextField(blank=True)
    dia_pago_mensual = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    plazo_notificacion_termino_dias = models.PositiveSmallIntegerField(default=60)
    dias_prealerta_admin = models.PositiveSmallIntegerField(default=90)
    estado = models.CharField(max_length=32, choices=EstadoContrato.choices, default=EstadoContrato.PENDING)
    identidad_envio_override = models.ForeignKey(
        IdentidadDeEnvio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='contratos_override',
    )
    politica_documental = models.ForeignKey(
        PoliticaFirmaYNotaria,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='contratos',
    )
    tiene_tramos = models.BooleanField(default=False)
    tiene_gastos_comunes = models.BooleanField(default=False)
    snapshot_representante_legal = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['codigo_contrato']

    def __str__(self):
        return self.codigo_contrato

    def principal_property_id(self):
        principal = self.contrato_propiedades.filter(rol_en_contrato=RolContratoPropiedad.PRIMARY).first()
        return principal.propiedad_id if principal else None

    def registration_date_for_retroactive_alert(self):
        if self.fecha_registro_operativo:
            return self.fecha_registro_operativo
        if self.created_at:
            return timezone.localtime(self.created_at).date()
        return None

    def retroactive_manual_notification_cutoff_date(self):
        if not self.fecha_inicio:
            return None
        return date(
            self.fecha_inicio.year,
            self.fecha_inicio.month,
            RETROACTIVE_MANUAL_NOTIFICATION_CUTOFF_DAY,
        )

    def requires_retroactive_manual_notification(self):
        registration_date = self.registration_date_for_retroactive_alert()
        cutoff_date = self.retroactive_manual_notification_cutoff_date()
        if not registration_date or not cutoff_date:
            return False
        return self.fecha_inicio <= registration_date and registration_date > cutoff_date

    def retroactive_manual_notification_alert(self):
        if not self.requires_retroactive_manual_notification():
            return ''
        registration_date = self.registration_date_for_retroactive_alert()
        return (
            'Contrato retroactivo registrado despues del dia 5 del mes operativo; '
            f'revisar posible notificacion manual antes de cobrar. Registro: {registration_date.isoformat()}.'
        )

    def blocks_automatic_past_billing(self, anio, mes):
        registration_date = self.fecha_registro_operativo
        if not registration_date or not self.fecha_inicio or self.fecha_inicio > registration_date:
            return False
        try:
            due_date = date(int(anio), int(mes), int(self.dia_pago_mensual))
        except (TypeError, ValueError):
            return False
        return due_date < registration_date

    def has_partial_early_termination_month(self):
        if self.estado != EstadoContrato.EARLY_TERMINATED or not self.fecha_fin_vigente:
            return False
        last_day = calendar.monthrange(self.fecha_fin_vigente.year, self.fecha_fin_vigente.month)[1]
        return self.fecha_fin_vigente.day != last_day

    def has_early_termination_proration_decision(self):
        return bool(
            (self.terminacion_anticipada_prorrata_ref or '').strip()
            and (self.terminacion_anticipada_prorrata_motivo or '').strip()
        )

    def allows_partial_early_termination_period(self, period_end):
        return (
            self.has_partial_early_termination_month()
            and self.has_early_termination_proration_decision()
            and period_end == self.fecha_fin_vigente
        )

    def validate_early_termination_proration(self):
        self.terminacion_anticipada_prorrata_ref = (self.terminacion_anticipada_prorrata_ref or '').strip()
        self.terminacion_anticipada_prorrata_motivo = (
            self.terminacion_anticipada_prorrata_motivo or ''
        ).strip()

        errors = {}
        if (
            self.terminacion_anticipada_prorrata_ref
            and not is_non_sensitive_reference(self.terminacion_anticipada_prorrata_ref)
        ):
            errors['terminacion_anticipada_prorrata_ref'] = (
                'La decision de prorrata por terminacion anticipada debe ser una referencia no sensible.'
            )

        if self.has_partial_early_termination_month():
            if not self.terminacion_anticipada_prorrata_ref:
                errors['terminacion_anticipada_prorrata_ref'] = (
                    'El ultimo mes parcial por terminacion anticipada requiere regla o decision auditada.'
                )
            if not self.terminacion_anticipada_prorrata_motivo:
                errors['terminacion_anticipada_prorrata_motivo'] = (
                    'El ultimo mes parcial por terminacion anticipada requiere motivo o criterio trazable.'
                )

        if errors:
            raise ValidationError(errors)

    def validate_identity_override(self):
        if not self.identidad_envio_override_id or not self.mandato_operacion_id:
            return

        if self.identidad_envio_override.estado != EstadoIdentidadEnvio.ACTIVE:
            raise ValidationError(
                {'identidad_envio_override': 'La identidad override del contrato debe estar activa.'}
            )

        identity_owner = (self.identidad_envio_override.owner_tipo, self.identidad_envio_override.owner_id)
        admin_tuple = self.mandato_operacion.administrador_tuple()
        facturadora_tuple = self.mandato_operacion.facturadora_tuple()
        propietario_tuple = self.mandato_operacion.propietario_tuple()

        if identity_owner not in {admin_tuple, facturadora_tuple}:
            raise ValidationError(
                {
                    'identidad_envio_override': (
                        'La identidad override debe pertenecer a la entidad facturadora o al administrador '
                        'operativo del mandato.'
                    )
                }
            )

        if identity_owner != propietario_tuple and not self.mandato_operacion.autoriza_comunicacion:
            raise ValidationError(
                {
                    'mandato_operacion': (
                        'El mandato debe autorizar comunicacion para usar una identidad override de un actor '
                        'distinto al propietario.'
                    )
                }
            )

    def validate_natural_tenant_document_profile(self):
        if not self.politica_documental_id or not self.arrendatario_id:
            return
        if self.arrendatario.tipo_arrendatario != TipoArrendatario.NATURAL:
            return

        missing_fields = []
        policy = self.politica_documental
        if policy.requiere_nacionalidad_arrendatario and not (self.arrendatario.nacionalidad or '').strip():
            missing_fields.append('nacionalidad')
        if policy.requiere_estado_civil_arrendatario and not self.arrendatario.estado_civil:
            missing_fields.append('estado civil')
        if policy.requiere_profesion_arrendatario and not (self.arrendatario.profesion or '').strip():
            missing_fields.append('profesion')

        if missing_fields:
            fields = ', '.join(missing_fields)
            raise ValidationError(
                {
                    'arrendatario': (
                        'La politica documental exige perfil de persona natural completo: '
                        f'{fields}.'
                    )
                }
            )

    def clean(self):
        super().clean()
        if self.fecha_fin_vigente < self.fecha_inicio:
            raise ValidationError({'fecha_fin_vigente': 'La fecha fin vigente no puede ser anterior al inicio.'})

        self.validate_early_termination_proration()
        self.validate_identity_override()

        if self.fecha_entrega and self.fecha_entrega < self.fecha_inicio:
            raise ValidationError({'fecha_entrega': 'La fecha de entrega no puede ser anterior al inicio.'})

        if self.plazo_notificacion_termino_dias <= 0:
            raise ValidationError(
                {'plazo_notificacion_termino_dias': 'El plazo de notificacion debe ser mayor que cero.'}
            )

        if self.dias_prealerta_admin <= 0:
            raise ValidationError({'dias_prealerta_admin': 'Los dias de prealerta deben ser mayores que cero.'})

        if self.estado in {EstadoContrato.ACTIVE, EstadoContrato.FUTURE}:
            if self.fecha_inicio.day != 1:
                raise ValidationError({'fecha_inicio': 'Un contrato vigente o futuro debe iniciar el dia 1.'})
            last_day = calendar.monthrange(self.fecha_fin_vigente.year, self.fecha_fin_vigente.month)[1]
            if self.fecha_fin_vigente.day != last_day:
                raise ValidationError(
                    {'fecha_fin_vigente': 'Un contrato vigente o futuro debe terminar el ultimo dia del mes.'}
                )
            if not self.politica_documental_id:
                raise ValidationError(
                    {'politica_documental': 'Un contrato vigente o futuro requiere politica documental.'}
                )
            if self.politica_documental.tipo_documental != TipoDocumental.MAIN_CONTRACT:
                raise ValidationError(
                    {
                        'politica_documental': (
                            'La politica documental del contrato debe ser de tipo contrato principal.'
                        )
                    }
                )
            if self.politica_documental.estado != EstadoPoliticaFirma.ACTIVE:
                raise ValidationError(
                    {'politica_documental': 'La politica documental del contrato debe estar activa.'}
                )
            self.validate_natural_tenant_document_profile()
            if self.mandato_operacion.estado != 'activa':
                raise ValidationError(
                    {'mandato_operacion': 'Un contrato vigente o futuro requiere un mandato operativo activo.'}
                )
            mandato_errors = []
            if self.mandato_operacion.vigencia_desde > self.fecha_inicio:
                mandato_errors.append('El mandato operativo debe estar vigente al inicio del contrato.')
            if (
                self.mandato_operacion.vigencia_hasta
                and self.mandato_operacion.vigencia_hasta < self.fecha_fin_vigente
            ):
                mandato_errors.append('El mandato operativo debe cubrir la fecha fin vigente del contrato.')
            if mandato_errors:
                raise ValidationError({'mandato_operacion': mandato_errors})
            if self.arrendatario_id and self.arrendatario.tipo_arrendatario == TipoArrendatario.COMPANY:
                self.snapshot_representante_legal = normalize_representante_legal_snapshot(
                    self.snapshot_representante_legal
                )


class ContratoPropiedad(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='contrato_propiedades',
    )
    propiedad = models.ForeignKey(
        'patrimonio.Propiedad',
        on_delete=models.PROTECT,
        related_name='contrato_propiedades',
    )
    rol_en_contrato = models.CharField(max_length=16, choices=RolContratoPropiedad.choices)
    porcentaje_distribucion_interna = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))],
    )
    codigo_conciliacion_efectivo_snapshot = models.CharField(max_length=3, validators=[codigo_efectivo_validator])

    class Meta:
        ordering = ['contrato_id', 'rol_en_contrato']
        constraints = [
            models.UniqueConstraint(
                fields=['contrato', 'propiedad'],
                name='uniq_propiedad_por_contrato',
            ),
        ]

    def __str__(self):
        return f'{self.contrato.codigo_contrato} - {self.propiedad.codigo_propiedad}'

    def clean(self):
        super().clean()
        if self.codigo_conciliacion_efectivo_snapshot == '000':
            raise ValidationError(
                {
                    'codigo_conciliacion_efectivo_snapshot': (
                        'El codigo efectivo debe estar en el rango 001-999.'
                    )
                }
            )
        if not self.contrato_id or not self.propiedad_id:
            return
        if self.contrato.estado not in {EstadoContrato.ACTIVE, EstadoContrato.FUTURE}:
            return

        if self.propiedad.estado != 'activa':
            raise ValidationError(
                {'propiedad': 'Un contrato vigente o futuro solo puede usar propiedades activas.'}
            )

        same_contract_links = ContratoPropiedad.objects.filter(contrato_id=self.contrato_id).exclude(pk=self.pk)
        if same_contract_links.count() >= 2:
            raise ValidationError(
                {'contrato': 'Un contrato vigente o futuro solo puede cubrir una propiedad o una pareja principal + vinculada.'}
            )
        primary_count = same_contract_links.filter(rol_en_contrato=RolContratoPropiedad.PRIMARY).count()
        linked_count = same_contract_links.filter(rol_en_contrato=RolContratoPropiedad.LINKED).count()
        if self.rol_en_contrato == RolContratoPropiedad.PRIMARY:
            primary_count += 1
        if self.rol_en_contrato == RolContratoPropiedad.LINKED:
            linked_count += 1
        total_links = same_contract_links.count() + 1
        if primary_count != 1:
            raise ValidationError(
                {'rol_en_contrato': 'Un contrato vigente o futuro debe tener exactamente una propiedad principal.'}
            )
        if total_links == 2 and linked_count != 1:
            raise ValidationError(
                {'rol_en_contrato': 'Una pareja de propiedades requiere una propiedad principal y una vinculada.'}
            )

        if self.rol_en_contrato == RolContratoPropiedad.PRIMARY:
            mismatched_contract_codes = same_contract_links.exclude(
                codigo_conciliacion_efectivo_snapshot=self.codigo_conciliacion_efectivo_snapshot,
            )
            if mismatched_contract_codes.exists():
                raise ValidationError(
                    {
                        'codigo_conciliacion_efectivo_snapshot': (
                            'La propiedad principal y la vinculada deben compartir el mismo codigo efectivo.'
                        )
                    }
                )
        else:
            primary_link = same_contract_links.filter(rol_en_contrato=RolContratoPropiedad.PRIMARY).first()
            if (
                primary_link
                and primary_link.codigo_conciliacion_efectivo_snapshot
                != self.codigo_conciliacion_efectivo_snapshot
            ):
                raise ValidationError(
                    {
                        'codigo_conciliacion_efectivo_snapshot': (
                            'La propiedad principal y la vinculada deben compartir el mismo codigo efectivo.'
                        )
                    }
                )

        same_state_links = ContratoPropiedad.objects.filter(
            propiedad_id=self.propiedad_id,
            contrato__estado=self.contrato.estado,
        ).exclude(pk=self.pk)
        if self.contrato_id:
            same_state_links = same_state_links.exclude(contrato_id=self.contrato_id)

        if same_state_links.exists():
            label = 'vigente' if self.contrato.estado == EstadoContrato.ACTIVE else 'futuro'
            raise ValidationError(
                {'propiedad': f'La propiedad ya participa en otro contrato {label}.'}
            )

        same_code_links = ContratoPropiedad.objects.filter(
            contrato__mandato_operacion__cuenta_recaudadora_id=(
                self.contrato.mandato_operacion.cuenta_recaudadora_id
            ),
            contrato__estado=self.contrato.estado,
            codigo_conciliacion_efectivo_snapshot=self.codigo_conciliacion_efectivo_snapshot,
        ).exclude(pk=self.pk)
        if self.contrato_id:
            same_code_links = same_code_links.exclude(contrato_id=self.contrato_id)

        if same_code_links.exists():
            label = 'vigente' if self.contrato.estado == EstadoContrato.ACTIVE else 'futuro'
            raise ValidationError(
                {
                    'codigo_conciliacion_efectivo_snapshot': (
                        f'El codigo efectivo ya esta usado en otro contrato {label} de la misma cuenta recaudadora.'
                    )
                }
            )


class PeriodoContractual(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='periodos_contractuales',
    )
    numero_periodo = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    monto_base = models.DecimalField(max_digits=14, decimal_places=2)
    moneda_base = models.CharField(max_length=8, choices=MonedaBaseContrato.choices)
    tipo_periodo = models.CharField(max_length=64)
    origen_periodo = models.CharField(max_length=64)
    politica_base_renovacion_ref = models.CharField(max_length=255, blank=True)
    politica_base_renovacion_motivo = models.TextField(blank=True)

    class Meta:
        ordering = ['contrato_id', 'numero_periodo']
        constraints = [
            models.UniqueConstraint(
                fields=['contrato', 'numero_periodo'],
                name='uniq_numero_periodo_por_contrato',
            ),
        ]

    def __str__(self):
        return f'{self.contrato.codigo_contrato} - Periodo {self.numero_periodo}'

    def is_renewal_period(self):
        return str(self.tipo_periodo or '').strip().lower() == RENEWAL_PERIOD_KIND

    def previous_period(self):
        if not self.contrato_id:
            return None
        return (
            PeriodoContractual.objects.filter(
                contrato_id=self.contrato_id,
                fecha_inicio__lt=self.fecha_inicio,
            )
            .exclude(pk=self.pk)
            .order_by('-fecha_inicio', '-numero_periodo')
            .first()
        )

    def has_renewal_base_policy(self):
        return bool(
            (self.politica_base_renovacion_ref or '').strip()
            and (self.politica_base_renovacion_motivo or '').strip()
        )

    def renewal_base_deviates_from_previous(self):
        if not self.contrato_id or not self.contrato.tiene_tramos or not self.is_renewal_period():
            return False
        previous = self.previous_period()
        if previous is None:
            return False
        return self.moneda_base != previous.moneda_base or Decimal(self.monto_base) != Decimal(previous.monto_base)

    def clean(self):
        super().clean()
        self.politica_base_renovacion_ref = (self.politica_base_renovacion_ref or '').strip()
        self.politica_base_renovacion_motivo = (self.politica_base_renovacion_motivo or '').strip()
        if self.fecha_fin < self.fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha fin del periodo no puede ser anterior al inicio.'})
        if self.fecha_inicio.day != 1:
            raise ValidationError({'fecha_inicio': 'El periodo contractual debe iniciar el primer dia del mes.'})
        last_day = calendar.monthrange(self.fecha_fin.year, self.fecha_fin.month)[1]
        allow_partial_final_period = (
            self.contrato_id
            and self.contrato.allows_partial_early_termination_period(self.fecha_fin)
        )
        if self.fecha_fin.day != last_day and not allow_partial_final_period:
            raise ValidationError({'fecha_fin': 'El periodo contractual debe terminar el ultimo dia del mes.'})
        if self.moneda_base == MonedaBaseContrato.CLP and self.monto_base < Decimal('1000.00'):
            raise ValidationError({'monto_base': 'Un periodo CLP debe respetar el minimo operativo de 1.000.'})
        if self.moneda_base == MonedaBaseContrato.UF and self.monto_base <= Decimal('0.00'):
            raise ValidationError({'monto_base': 'Un periodo UF debe tener monto positivo.'})
        if bool(self.politica_base_renovacion_ref) != bool(self.politica_base_renovacion_motivo):
            raise ValidationError(
                {
                    'politica_base_renovacion_ref': (
                        'La politica de base de renovacion requiere referencia y motivo trazable.'
                    )
                }
            )
        if self.politica_base_renovacion_ref and not is_non_sensitive_reference(
            self.politica_base_renovacion_ref
        ):
            raise ValidationError(
                {
                    'politica_base_renovacion_ref': (
                        'La politica de base de renovacion debe usar una referencia no sensible.'
                    )
                }
            )
        if not self.contrato_id:
            return

        errors = {}
        if self.fecha_inicio < self.contrato.fecha_inicio:
            errors['fecha_inicio'] = 'El periodo no puede iniciar antes de la vigencia del contrato.'
        if self.fecha_fin > self.contrato.fecha_fin_vigente:
            errors['fecha_fin'] = 'El periodo no puede terminar despues de la vigencia del contrato.'
        earlier_periods = PeriodoContractual.objects.filter(
            contrato_id=self.contrato_id,
            fecha_inicio__lt=self.fecha_inicio,
        ).exclude(pk=self.pk)
        expected_number = earlier_periods.count() + 1
        if self.numero_periodo != expected_number:
            errors['numero_periodo'] = (
                'El numero de periodo debe coincidir con el orden cronologico dentro del contrato.'
            )
        if self.renewal_base_deviates_from_previous() and not self.has_renewal_base_policy():
            errors['politica_base_renovacion_ref'] = (
                'Una renovacion con base distinta al ultimo tramo vigente requiere politica documentada.'
            )
        if errors:
            raise ValidationError(errors)


class CodeudorSolidario(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='codeudores_solidarios',
    )
    snapshot_identidad = models.JSONField(default=dict)
    fecha_inclusion = models.DateField(default=timezone.localdate)
    estado = models.CharField(
        max_length=16,
        choices=EstadoCodeudorSolidario.choices,
        default=EstadoCodeudorSolidario.ACTIVE,
    )

    class Meta:
        ordering = ['contrato_id', 'fecha_inclusion']

    def __str__(self):
        return f'{self.contrato.codigo_contrato} - Codeudor {self.pk}'

    def clean(self):
        super().clean()
        snapshot = self.snapshot_identidad or {}
        if not isinstance(snapshot, dict):
            raise ValidationError(
                {'snapshot_identidad': 'El snapshot del codeudor debe ser un objeto con nombre y RUT.'}
            )

        nombre = str(snapshot.get('nombre') or '').strip()
        rut_value = str(snapshot.get('rut') or '').strip()
        if not nombre or not rut_value:
            raise ValidationError(
                {'snapshot_identidad': 'El snapshot del codeudor debe incluir nombre y RUT.'}
            )

        try:
            normalized_rut = validate_rut(rut_value)
        except ValidationError as error:
            raise ValidationError({'snapshot_identidad': error.messages}) from error

        if self.estado != EstadoCodeudorSolidario.ACTIVE or not self.contrato_id:
            return

        active_codebtors = CodeudorSolidario.objects.filter(
            contrato_id=self.contrato_id,
            estado=EstadoCodeudorSolidario.ACTIVE,
        ).exclude(pk=self.pk)
        if active_codebtors.count() >= 3:
            raise ValidationError({'estado': 'Un contrato admite como maximo 3 codeudores solidarios activos.'})

        for codebtor in active_codebtors:
            other_snapshot = codebtor.snapshot_identidad or {}
            if not isinstance(other_snapshot, dict):
                continue
            try:
                other_rut = validate_rut(other_snapshot.get('rut'))
            except ValidationError:
                continue
            if other_rut == normalized_rut:
                raise ValidationError(
                    {'snapshot_identidad': 'No puede repetir el mismo codeudor activo dentro del contrato.'}
                )


class AvisoTermino(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='avisos_termino',
    )
    fecha_efectiva = models.DateField()
    causal = models.CharField(max_length=255)
    estado = models.CharField(max_length=16, choices=EstadoAvisoTermino.choices, default=EstadoAvisoTermino.DRAFT)
    resolucion_conflicto_renovacion_ref = models.CharField(max_length=255, blank=True)
    resolucion_conflicto_renovacion_motivo = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='avisos_termino_registrados',
    )

    class Meta:
        ordering = ['-fecha_efectiva']
        constraints = [
            models.UniqueConstraint(
                fields=['contrato'],
                condition=Q(estado='registrado'),
                name='uniq_aviso_registrado_por_contrato',
            ),
        ]

    def __str__(self):
        return f'{self.contrato.codigo_contrato} - {self.estado}'

    def latest_timely_registration_at(self):
        if not self.contrato_id or not self.contrato.fecha_fin_vigente:
            return None
        deadline_date = self.contrato.fecha_fin_vigente - timedelta(
            days=self.contrato.plazo_notificacion_termino_dias
        )
        return timezone.make_aware(
            datetime.combine(deadline_date, NOTICE_DEADLINE_END_OF_DAY),
            timezone.get_current_timezone(),
        )

    def registration_timestamp_for_notice_deadline(self):
        return self.created_at

    def has_renewal_conflict_resolution(self):
        return bool(
            (self.resolucion_conflicto_renovacion_ref or '').strip()
            and (self.resolucion_conflicto_renovacion_motivo or '').strip()
        )

    def has_executed_renewal_conflict(self, future_start_date=None):
        if self.estado != EstadoAvisoTermino.REGISTERED or not self.contrato_id:
            return False
        if future_start_date is None:
            future_start_date = self.fecha_efectiva
        return self.contrato.periodos_contractuales.filter(
            tipo_periodo__iexact=RENEWAL_PERIOD_KIND,
            fecha_inicio__lte=future_start_date,
            fecha_fin__gte=future_start_date,
        ).exists()

    def is_late_registered_notice(self):
        if self.estado != EstadoAvisoTermino.REGISTERED:
            return False
        registration_timestamp = self.registration_timestamp_for_notice_deadline()
        latest_timely_registration = self.latest_timely_registration_at()
        if not registration_timestamp or not latest_timely_registration:
            return False
        if timezone.is_naive(registration_timestamp):
            registration_timestamp = timezone.make_aware(
                registration_timestamp,
                timezone.get_current_timezone(),
            )
        return registration_timestamp > latest_timely_registration

    def late_registration_alert(self):
        if not self.is_late_registered_notice():
            return ''
        registration_timestamp = self.registration_timestamp_for_notice_deadline()
        latest_timely_registration = self.latest_timely_registration_at()
        return (
            'Aviso de termino registrado fuera del plazo contractual; '
            f'limite oportuno: {latest_timely_registration.isoformat()}; '
            f'registro real: {registration_timestamp.isoformat()}.'
        )

    def clean(self):
        super().clean()
        self.resolucion_conflicto_renovacion_ref = (self.resolucion_conflicto_renovacion_ref or '').strip()
        self.resolucion_conflicto_renovacion_motivo = (
            self.resolucion_conflicto_renovacion_motivo or ''
        ).strip()
        if self.fecha_efectiva < self.contrato.fecha_inicio:
            raise ValidationError({'fecha_efectiva': 'La fecha efectiva no puede ser anterior al inicio del contrato.'})
        if self.fecha_efectiva > self.contrato.fecha_fin_vigente:
            raise ValidationError(
                {'fecha_efectiva': 'La fecha efectiva no puede ser posterior a la fecha fin vigente del contrato.'}
            )
        if (
            self.resolucion_conflicto_renovacion_ref
            and not is_non_sensitive_reference(self.resolucion_conflicto_renovacion_ref)
        ):
            raise ValidationError(
                {
                    'resolucion_conflicto_renovacion_ref': (
                        'La resolucion guiada del conflicto de renovacion debe usar una referencia no sensible.'
                    )
                }
            )
        if self.resolucion_conflicto_renovacion_ref and not self.resolucion_conflicto_renovacion_motivo:
            raise ValidationError(
                {
                    'resolucion_conflicto_renovacion_motivo': (
                        'La resolucion guiada del conflicto de renovacion requiere motivo o criterio trazable.'
                    )
                }
            )
        if self.resolucion_conflicto_renovacion_motivo and not self.resolucion_conflicto_renovacion_ref:
            raise ValidationError(
                {
                    'resolucion_conflicto_renovacion_ref': (
                        'La resolucion guiada del conflicto de renovacion requiere referencia no sensible.'
                    )
                }
            )

        if self.estado == EstadoAvisoTermino.CANCELED:
            principal_ids = list(
                self.contrato.contrato_propiedades.filter(
                    rol_en_contrato=RolContratoPropiedad.PRIMARY
                ).values_list('propiedad_id', flat=True)
            )
            if principal_ids:
                future_exists = Contrato.objects.filter(
                    estado=EstadoContrato.FUTURE,
                    contrato_propiedades__propiedad_id__in=principal_ids,
                    contrato_propiedades__rol_en_contrato=RolContratoPropiedad.PRIMARY,
                ).exclude(pk=self.contrato_id).exists()
                if future_exists:
                    raise ValidationError(
                        {'estado': 'No se puede cancelar el aviso si existe un contrato futuro activo para la propiedad principal.'}
                    )

