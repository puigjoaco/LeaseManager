from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EstadoExpediente(models.TextChoices):
    OPEN = 'abierto', 'Abierto'
    CLOSED = 'cerrado', 'Cerrado'
    ARCHIVED = 'archivado', 'Archivado'


class TipoDocumental(models.TextChoices):
    MAIN_CONTRACT = 'contrato_principal', 'Contrato principal'
    ADDENDUM = 'anexo', 'Anexo'
    NOTICE_LETTER = 'carta_aviso', 'Carta de aviso'
    GUARANTEE_STATEMENT = 'liquidacion_garantia', 'Liquidacion de garantia'
    TAX_SUPPORT = 'respaldo_tributario', 'Respaldo tributario'
    NOTARY_RECEIPT = 'comprobante_notarial', 'Comprobante notarial'
    MANUAL_EVIDENCE = 'evidencia_resolucion_manual', 'Evidencia de resolucion manual'


class OrigenDocumento(models.TextChoices):
    GENERATED = 'generado_sistema', 'Generado por sistema'
    EXTERNAL_UPLOAD = 'carga_externa_controlada', 'Carga externa controlada'


class EstadoDocumento(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    ISSUED = 'emitido', 'Emitido'
    FORMALIZED = 'formalizado', 'Formalizado'
    ARCHIVED = 'archivado', 'Archivado'
    CANCELED = 'cancelado', 'Cancelado'


class EstadoPoliticaFirma(models.TextChoices):
    ACTIVE = 'activa', 'Activa'
    INACTIVE = 'inactiva', 'Inactiva'


class ModoFirmaPermitido(models.TextChoices):
    SIMPLE = 'firma_simple', 'Firma simple'
    ADVANCED = 'firma_avanzada', 'Firma avanzada'
    MIXED = 'mixta', 'Mixta'
    MANUAL = 'manual', 'Manual'


class ExpedienteDocumental(TimestampedModel):
    entidad_tipo = models.CharField(max_length=64)
    entidad_id = models.CharField(max_length=64)
    estado = models.CharField(max_length=16, choices=EstadoExpediente.choices, default=EstadoExpediente.OPEN)
    owner_operativo = models.CharField(max_length=128)

    class Meta:
        ordering = ['entidad_tipo', 'entidad_id']
        constraints = [
            models.UniqueConstraint(
                fields=['entidad_tipo', 'entidad_id'],
                name='uniq_expediente_por_entidad',
            ),
        ]

    def __str__(self):
        return f'{self.entidad_tipo}:{self.entidad_id}'


class PoliticaFirmaYNotaria(TimestampedModel):
    tipo_documental = models.CharField(max_length=64, choices=TipoDocumental.choices, unique=True)
    requiere_firma_arrendador = models.BooleanField(default=False)
    requiere_firma_arrendatario = models.BooleanField(default=False)
    requiere_codeudor = models.BooleanField(default=False)
    requiere_notaria = models.BooleanField(default=False)
    modo_firma_permitido = models.CharField(
        max_length=32,
        choices=ModoFirmaPermitido.choices,
        default=ModoFirmaPermitido.SIMPLE,
    )
    estado = models.CharField(max_length=16, choices=EstadoPoliticaFirma.choices, default=EstadoPoliticaFirma.ACTIVE)

    class Meta:
        ordering = ['tipo_documental']

    def __str__(self):
        return self.tipo_documental

    def clean(self):
        super().clean()
        if self.tipo_documental == TipoDocumental.MAIN_CONTRACT:
            if not self.requiere_firma_arrendador or not self.requiere_firma_arrendatario:
                raise ValidationError(
                    'El ContratoPrincipal requiere firma de arrendador y arrendatario.'
                )


class DocumentoEmitido(TimestampedModel):
    expediente = models.ForeignKey(
        ExpedienteDocumental,
        on_delete=models.CASCADE,
        related_name='documentos_emitidos',
    )
    tipo_documental = models.CharField(max_length=64, choices=TipoDocumental.choices)
    version_plantilla = models.CharField(max_length=64)
    checksum = models.CharField(max_length=128)
    fecha_carga = models.DateTimeField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='documentos_emitidos',
    )
    origen = models.CharField(max_length=32, choices=OrigenDocumento.choices)
    estado = models.CharField(max_length=16, choices=EstadoDocumento.choices, default=EstadoDocumento.DRAFT)
    storage_ref = models.CharField(max_length=255)
    firma_arrendador_registrada = models.BooleanField(default=False)
    firma_arrendatario_registrada = models.BooleanField(default=False)
    firma_codeudor_registrada = models.BooleanField(default=False)
    recepcion_notarial_registrada = models.BooleanField(default=False)
    comprobante_notarial = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='documentos_formalizados',
    )

    class Meta:
        ordering = ['-fecha_carga', '-id']

    def __str__(self):
        return f'{self.expediente_id} - {self.tipo_documental}'

    def get_active_policy(self):
        return PoliticaFirmaYNotaria.objects.filter(tipo_documental=self.tipo_documental, estado=EstadoPoliticaFirma.ACTIVE).first()

    def clean(self):
        super().clean()
        if self.comprobante_notarial_id and self.comprobante_notarial.tipo_documental != TipoDocumental.NOTARY_RECEIPT:
            raise ValidationError({'comprobante_notarial': 'El comprobante vinculado debe ser un comprobante notarial.'})

        if self.estado == EstadoDocumento.FORMALIZED:
            self.validate_formalization()

    def validate_formalization(self):
        policy = self.get_active_policy()
        if not policy:
            raise ValidationError({'estado': 'No existe una politica activa para formalizar este tipo documental.'})

        if policy.requiere_firma_arrendador and not self.firma_arrendador_registrada:
            raise ValidationError({'estado': 'Falta registrar la firma del arrendador.'})
        if policy.requiere_firma_arrendatario and not self.firma_arrendatario_registrada:
            raise ValidationError({'estado': 'Falta registrar la firma del arrendatario.'})
        if policy.requiere_codeudor and not self.firma_codeudor_registrada:
            raise ValidationError({'estado': 'Falta registrar la firma del codeudor.'})
        if policy.requiere_notaria:
            if not self.recepcion_notarial_registrada:
                raise ValidationError({'estado': 'Falta registrar la recepcion notarial.'})
            if not self.comprobante_notarial_id:
                raise ValidationError({'estado': 'Falta archivar el comprobante notarial exigido por la politica.'})

