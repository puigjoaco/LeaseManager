import re

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.reference_validation import (
    contains_sensitive_control_reference,
    is_non_sensitive_control_reference,
    is_non_sensitive_reference,
    normalize_reference,
)


DOCUMENT_CHECKSUM_PATTERN = re.compile(r'^[0-9a-f]{64}$')


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


class CategoriaArchivoExpediente(models.TextChoices):
    IMAGE = 'imagen', 'Imagen'
    VIDEO = 'video', 'Video'
    SPREADSHEET = 'planilla', 'Planilla'
    TEXT = 'texto', 'Texto'
    SOURCE_DOCUMENT = 'documento_fuente', 'Documento fuente'
    ARCHIVE = 'comprimido', 'Comprimido'
    OPERATIONAL_EVIDENCE = 'evidencia_operacional', 'Evidencia operacional'
    OTHER = 'otro', 'Otro'


class EstadoClasificacionArchivoExpediente(models.TextChoices):
    CONFIRMED = 'confirmado', 'Confirmado'
    PROBABLE = 'probable', 'Probable'
    NEEDS_MANUAL_REVIEW = 'requiere_revision_manual', 'Requiere revision manual'
    EXACT_DUPLICATE = 'duplicado_exactamente', 'Duplicado exactamente'
    CANONICAL_ALIAS = 'alias_de_canonico', 'Alias de canonico'
    NOT_LOADABLE_WITHOUT_DECISION = 'no_cargable_sin_decision', 'No cargable sin decision'


class EstadoPoliticaFirma(models.TextChoices):
    ACTIVE = 'activa', 'Activa'
    INACTIVE = 'inactiva', 'Inactiva'


class EstadoPlantillaDocumental(models.TextChoices):
    ACTIVE = 'activa', 'Activa'
    INACTIVE = 'inactiva', 'Inactiva'


class ModoFirmaPermitido(models.TextChoices):
    SIMPLE = 'firma_simple', 'Firma simple'
    ADVANCED = 'firma_avanzada', 'Firma avanzada'
    MIXED = 'mixta', 'Mixta'
    MANUAL = 'manual', 'Manual'


def is_pdf_storage_ref(value):
    normalized = str(value or '').strip().lower().split('?', 1)[0].split('#', 1)[0]
    return normalized.endswith('.pdf')


def is_valid_pdf_checksum(value):
    return bool(DOCUMENT_CHECKSUM_PATTERN.fullmatch(str(value or '')))


def is_valid_sha256_checksum(value):
    return is_valid_pdf_checksum(value)


def normalize_pdf_checksum(value):
    return normalize_reference(value).lower()


def _normalize_text_fields(instance, field_names):
    for field_name in field_names:
        setattr(instance, field_name, normalize_reference(getattr(instance, field_name, '')))


def _normalize_checksum_fields(instance, field_names):
    for field_name in field_names:
        setattr(instance, field_name, normalize_pdf_checksum(getattr(instance, field_name, '')))


class OperationalDocumentTextNormalizationMixin:
    operational_text_fields = ()
    checksum_fields = ()

    def _normalize_operational_text_fields(self):
        _normalize_text_fields(self, self.operational_text_fields)
        _normalize_checksum_fields(self, self.checksum_fields)

    def full_clean(self, *args, **kwargs):
        self._normalize_operational_text_fields()
        return super().full_clean(*args, **kwargs)

    def clean(self):
        self._normalize_operational_text_fields()
        return super().clean()

    def save(self, *args, **kwargs):
        self._normalize_operational_text_fields()
        return super().save(*args, **kwargs)


def has_active_document_template(tipo_documental, version_plantilla):
    return PlantillaDocumental.objects.filter(
        tipo_documental=tipo_documental,
        version_plantilla=str(version_plantilla or '').strip(),
        estado=EstadoPlantillaDocumental.ACTIVE,
    ).exists()


def _contract_id_from_expediente(expediente):
    if not expediente or expediente.entidad_tipo != 'contrato':
        return None
    try:
        return int(str(expediente.entidad_id).strip())
    except (TypeError, ValueError):
        return None


class ExpedienteDocumental(OperationalDocumentTextNormalizationMixin, TimestampedModel):
    operational_text_fields = ('entidad_tipo', 'entidad_id', 'owner_operativo')

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

    def clean(self):
        super().clean()
        field_labels = {
            'entidad_tipo': 'entidad_tipo',
            'entidad_id': 'entidad_id',
            'owner_operativo': 'owner_operativo',
        }
        errors = {}
        for field_name, label in field_labels.items():
            if not is_non_sensitive_reference(getattr(self, field_name)):
                errors[field_name] = f'{label} debe ser una referencia operativa no sensible.'
        if errors:
            raise ValidationError(errors)


class PoliticaFirmaYNotaria(TimestampedModel):
    tipo_documental = models.CharField(max_length=64, choices=TipoDocumental.choices, unique=True)
    requiere_firma_arrendador = models.BooleanField(default=False)
    requiere_firma_arrendatario = models.BooleanField(default=False)
    requiere_codeudor = models.BooleanField(default=False)
    requiere_nacionalidad_arrendatario = models.BooleanField(default=False)
    requiere_estado_civil_arrendatario = models.BooleanField(default=False)
    requiere_profesion_arrendatario = models.BooleanField(default=False)
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

    def persisted_policy(self):
        if not self.pk:
            return None
        return type(self).objects.filter(pk=self.pk).only(
            'tipo_documental',
            'requiere_firma_arrendador',
            'requiere_firma_arrendatario',
            'requiere_codeudor',
            'requiere_nacionalidad_arrendatario',
            'requiere_estado_civil_arrendatario',
            'requiere_profesion_arrendatario',
            'requiere_notaria',
            'modo_firma_permitido',
            'estado',
        ).first()

    def clean(self):
        super().clean()
        errors = {}
        if self.tipo_documental == TipoDocumental.MAIN_CONTRACT:
            if not self.requiere_firma_arrendador or not self.requiere_firma_arrendatario:
                errors['tipo_documental'] = 'El ContratoPrincipal requiere firma de arrendador y arrendatario.'

        if (
            self.tipo_documental != TipoDocumental.MAIN_CONTRACT
            and (
                self.requiere_nacionalidad_arrendatario
                or self.requiere_estado_civil_arrendatario
                or self.requiere_profesion_arrendatario
            )
        ):
            errors['tipo_documental'] = (
                'Los requisitos documentales del arrendatario persona natural solo aplican al contrato principal.'
            )

        persisted = self.persisted_policy()
        if persisted:
            policy_is_used = DocumentoEmitido.objects.filter(tipo_documental=persisted.tipo_documental).exists()
            if policy_is_used:
                protected_fields = (
                    'tipo_documental',
                    'requiere_firma_arrendador',
                    'requiere_firma_arrendatario',
                    'requiere_codeudor',
                    'requiere_nacionalidad_arrendatario',
                    'requiere_estado_civil_arrendatario',
                    'requiere_profesion_arrendatario',
                    'requiere_notaria',
                    'modo_firma_permitido',
                    'estado',
                )
                for field in protected_fields:
                    if getattr(self, field) != getattr(persisted, field):
                        errors[field] = (
                            'No se puede modificar una politica documental ya usada por documentos emitidos.'
                        )

        if errors:
            raise ValidationError(errors)


class PlantillaDocumental(OperationalDocumentTextNormalizationMixin, TimestampedModel):
    operational_text_fields = ('version_plantilla', 'plantilla_ref', 'checksum_plantilla', 'descripcion')
    checksum_fields = ('checksum_plantilla',)

    tipo_documental = models.CharField(max_length=64, choices=TipoDocumental.choices)
    version_plantilla = models.CharField(max_length=64)
    plantilla_ref = models.CharField(max_length=255)
    checksum_plantilla = models.CharField(max_length=128)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=16, choices=EstadoPlantillaDocumental.choices, default=EstadoPlantillaDocumental.ACTIVE)

    class Meta:
        ordering = ['tipo_documental', 'version_plantilla']
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_documental', 'version_plantilla'],
                name='uniq_plantilla_documental_version',
            ),
        ]

    def __str__(self):
        return f'{self.tipo_documental}:{self.version_plantilla}'

    def persisted_template(self):
        if not self.pk:
            return None
        return type(self).objects.filter(pk=self.pk).only(
            'tipo_documental',
            'version_plantilla',
            'plantilla_ref',
            'checksum_plantilla',
            'estado',
        ).first()

    def clean(self):
        super().clean()
        errors = {}
        if not str(self.version_plantilla or '').strip():
            errors['version_plantilla'] = 'La plantilla documental requiere version_plantilla.'
        if not is_non_sensitive_reference(self.plantilla_ref):
            errors['plantilla_ref'] = 'plantilla_ref debe ser una referencia no sensible.'
        if not is_valid_pdf_checksum(self.checksum_plantilla):
            errors['checksum_plantilla'] = 'checksum_plantilla debe ser SHA-256 hexadecimal canonico.'
        persisted = self.persisted_template()
        if persisted:
            template_is_used = DocumentoEmitido.objects.filter(
                tipo_documental=persisted.tipo_documental,
                version_plantilla=persisted.version_plantilla,
            ).exists()
            if template_is_used:
                protected_fields = (
                    'tipo_documental',
                    'version_plantilla',
                    'plantilla_ref',
                    'checksum_plantilla',
                    'estado',
                )
                for field in protected_fields:
                    if getattr(self, field) != getattr(persisted, field):
                        errors[field] = (
                            'No se puede modificar una plantilla documental ya usada por documentos emitidos.'
                        )
        if errors:
            raise ValidationError(errors)


class DocumentoEmitido(OperationalDocumentTextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'version_plantilla',
        'checksum',
        'storage_ref',
        'evidencia_formalizacion_ref',
        'correccion_ref',
    )
    checksum_fields = ('checksum',)

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
    evidencia_formalizacion_ref = models.CharField(max_length=128, blank=True)
    comprobante_notarial = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='documentos_formalizados',
    )
    documento_origen = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='versiones_correctivas',
    )
    correccion_ref = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ['-fecha_carga', '-id']

    def __str__(self):
        return f'{self.expediente_id} - {self.tipo_documental}'

    def get_active_policy(self):
        return PoliticaFirmaYNotaria.objects.filter(tipo_documental=self.tipo_documental, estado=EstadoPoliticaFirma.ACTIVE).first()

    def contract_has_active_codebtor(self):
        if not self.expediente_id:
            return False
        contrato_id = _contract_id_from_expediente(self.expediente)
        if contrato_id is None:
            return False
        codebtor_model = apps.get_model('contratos', 'CodeudorSolidario')
        return codebtor_model.objects.filter(contrato_id=contrato_id, estado='activo').exists()

    def requires_codebtor_signature(self, policy=None):
        effective_policy = policy or self.get_active_policy()
        return bool(effective_policy and effective_policy.requiere_codeudor and self.contract_has_active_codebtor())

    def clean(self):
        super().clean()
        if self.checksum and not is_valid_pdf_checksum(self.checksum):
            raise ValidationError(
                {'checksum': 'checksum debe ser un digest SHA-256 hexadecimal canonico de 64 caracteres.'}
            )
        if self.storage_ref and not is_pdf_storage_ref(self.storage_ref):
            raise ValidationError({'storage_ref': 'El documento canonico debe referenciar un PDF.'})
        if self.storage_ref and not is_non_sensitive_reference(self.storage_ref):
            raise ValidationError(
                {'storage_ref': 'storage_ref debe ser una referencia PDF no sensible, no una URL, token o credencial.'}
            )
        if self.evidencia_formalizacion_ref and not is_non_sensitive_reference(self.evidencia_formalizacion_ref):
            raise ValidationError(
                {'evidencia_formalizacion_ref': 'evidencia_formalizacion_ref debe ser una referencia no sensible.'}
            )
        if not self.usuario_id:
            raise ValidationError({'usuario': 'Documento emitido requiere usuario responsable de carga.'})
        if not self.get_active_policy():
            raise ValidationError({'tipo_documental': 'Documento emitido requiere politica activa para su tipo documental.'})
        if not has_active_document_template(self.tipo_documental, self.version_plantilla):
            raise ValidationError(
                {'version_plantilla': 'Documento emitido requiere plantilla documental activa para tipo y version.'}
            )
        if self.comprobante_notarial_id and self.comprobante_notarial.tipo_documental != TipoDocumental.NOTARY_RECEIPT:
            raise ValidationError({'comprobante_notarial': 'El comprobante vinculado debe ser un comprobante notarial.'})
        if self.comprobante_notarial_id and self.pk and self.comprobante_notarial_id == self.pk:
            raise ValidationError({'comprobante_notarial': 'Un documento no puede usarse como su propio comprobante notarial.'})
        if self.comprobante_notarial_id and self.comprobante_notarial.expediente_id != self.expediente_id:
            raise ValidationError(
                {'comprobante_notarial': 'El comprobante notarial debe pertenecer al mismo expediente documental.'}
            )
        if self.comprobante_notarial_id and self.comprobante_notarial.estado in {
            EstadoDocumento.DRAFT,
            EstadoDocumento.CANCELED,
        }:
            raise ValidationError(
                {'comprobante_notarial': 'El comprobante notarial debe estar emitido, formalizado o archivado.'}
            )
        if self.correccion_ref and not self.documento_origen_id:
            raise ValidationError(
                {'documento_origen': 'Una referencia de correccion requiere documento formalizado de origen.'}
            )
        if self.documento_origen_id:
            self.validate_corrective_version()

        if self.estado == EstadoDocumento.FORMALIZED:
            self.validate_formalization()

    def validate_corrective_version(self):
        origin = self.documento_origen
        if self.pk and self.documento_origen_id == self.pk:
            raise ValidationError({'documento_origen': 'Un documento no puede corregirse a si mismo.'})
        if origin.estado != EstadoDocumento.FORMALIZED:
            raise ValidationError({'documento_origen': 'La version correctiva debe referenciar un documento formalizado.'})
        if origin.expediente_id != self.expediente_id:
            raise ValidationError({'documento_origen': 'La version correctiva debe pertenecer al mismo expediente.'})
        if origin.tipo_documental != self.tipo_documental:
            raise ValidationError({'documento_origen': 'La version correctiva debe conservar el tipo documental.'})
        if not str(self.correccion_ref or '').strip():
            raise ValidationError({'correccion_ref': 'La version correctiva requiere referencia no sensible de motivo.'})
        if not is_non_sensitive_reference(self.correccion_ref):
            raise ValidationError({'correccion_ref': 'correccion_ref debe ser una referencia no sensible.'})
        if normalize_pdf_checksum(self.checksum) == normalize_pdf_checksum(origin.checksum):
            raise ValidationError({'checksum': 'La version correctiva debe tener checksum propio distinto al documento origen.'})
        if str(self.storage_ref or '').strip() == str(origin.storage_ref or '').strip():
            raise ValidationError({'storage_ref': 'La version correctiva debe tener PDF propio distinto al documento origen.'})

    def validate_formalization(self):
        policy = self.get_active_policy()
        if not policy:
            raise ValidationError({'estado': 'No existe una politica activa para formalizar este tipo documental.'})
        if not str(self.evidencia_formalizacion_ref or '').strip():
            raise ValidationError(
                {'evidencia_formalizacion_ref': 'La formalizacion requiere una referencia no sensible de evidencia.'}
            )

        if policy.requiere_firma_arrendador and not self.firma_arrendador_registrada:
            raise ValidationError({'estado': 'Falta registrar la firma del arrendador.'})
        if policy.requiere_firma_arrendatario and not self.firma_arrendatario_registrada:
            raise ValidationError({'estado': 'Falta registrar la firma del arrendatario.'})
        if self.requires_codebtor_signature(policy) and not self.firma_codeudor_registrada:
            raise ValidationError({'estado': 'Falta registrar la firma del codeudor.'})
        if policy.requiere_notaria:
            if not self.recepcion_notarial_registrada:
                raise ValidationError({'estado': 'Falta registrar la recepcion notarial.'})
            if not self.comprobante_notarial_id:
                raise ValidationError({'estado': 'Falta archivar el comprobante notarial exigido por la politica.'})


class ArchivoExpediente(OperationalDocumentTextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'categoria',
        'subcategoria',
        'titulo_operativo',
        'descripcion_objetiva',
        'extension',
        'mime_type',
        'checksum_sha256',
        'storage_ref',
        'origen_auditoria',
        'estado_clasificacion',
    )
    checksum_fields = ('checksum_sha256',)

    expediente = models.ForeignKey(
        ExpedienteDocumental,
        on_delete=models.CASCADE,
        related_name='archivos_expediente',
    )
    categoria = models.CharField(max_length=32, choices=CategoriaArchivoExpediente.choices)
    subcategoria = models.CharField(max_length=64, blank=True)
    titulo_operativo = models.CharField(max_length=255)
    descripcion_objetiva = models.TextField(blank=True)
    extension = models.CharField(max_length=16)
    mime_type = models.CharField(max_length=128, blank=True)
    checksum_sha256 = models.CharField(max_length=128)
    size_bytes = models.PositiveBigIntegerField()
    storage_ref = models.CharField(max_length=255)
    origen_auditoria = models.CharField(max_length=128)
    estado_clasificacion = models.CharField(
        max_length=32,
        choices=EstadoClasificacionArchivoExpediente.choices,
        default=EstadoClasificacionArchivoExpediente.CONFIRMED,
    )
    duplicate_of = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='duplicados',
    )
    fecha_archivo = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['expediente_id', 'categoria', 'subcategoria', 'titulo_operativo', 'id']
        indexes = [
            models.Index(fields=['checksum_sha256'], name='idx_archivo_exp_checksum'),
            models.Index(fields=['categoria', 'estado_clasificacion'], name='idx_archivo_exp_cat_estado'),
        ]

    def __str__(self):
        return f'{self.expediente_id} - {self.categoria} - {self.titulo_operativo}'

    def _normalize_operational_text_fields(self):
        super()._normalize_operational_text_fields()
        self.extension = str(self.extension or '').strip().lower()
        if self.extension and not self.extension.startswith('.'):
            self.extension = f'.{self.extension}'

    def clean(self):
        super().clean()
        errors = {}
        if not str(self.titulo_operativo or '').strip():
            errors['titulo_operativo'] = 'Archivo de expediente requiere titulo_operativo.'
        if not str(self.origen_auditoria or '').strip():
            errors['origen_auditoria'] = 'Archivo de expediente requiere origen_auditoria.'
        if not is_valid_sha256_checksum(self.checksum_sha256):
            errors['checksum_sha256'] = 'checksum_sha256 debe ser SHA-256 hexadecimal canonico.'
        if not self.extension or len(self.extension) < 2:
            errors['extension'] = 'extension debe indicar la extension original, por ejemplo .jpg.'
        if self.storage_ref and not is_non_sensitive_control_reference(self.storage_ref):
            errors['storage_ref'] = 'storage_ref debe ser una referencia no sensible, sin URL, token, RUT ni ruta local.'
        if self.origen_auditoria and contains_sensitive_control_reference(self.origen_auditoria):
            errors['origen_auditoria'] = 'origen_auditoria no debe contener referencias sensibles.'
        if self.titulo_operativo and contains_sensitive_control_reference(self.titulo_operativo):
            errors['titulo_operativo'] = 'titulo_operativo no debe contener referencias sensibles.'
        if self.descripcion_objetiva and contains_sensitive_control_reference(self.descripcion_objetiva):
            errors['descripcion_objetiva'] = 'descripcion_objetiva no debe contener referencias sensibles.'
        if self.duplicate_of_id and self.pk and self.duplicate_of_id == self.pk:
            errors['duplicate_of'] = 'Un archivo no puede duplicarse a si mismo.'
        if (
            self.estado_clasificacion
            in {
                EstadoClasificacionArchivoExpediente.EXACT_DUPLICATE,
                EstadoClasificacionArchivoExpediente.CANONICAL_ALIAS,
            }
            and not self.duplicate_of_id
        ):
            errors['duplicate_of'] = 'Duplicados y alias requieren referencia al archivo canonico.'
        if (
            self.duplicate_of_id
            and self.duplicate_of
            and self.estado_clasificacion == EstadoClasificacionArchivoExpediente.EXACT_DUPLICATE
            and self.checksum_sha256 != self.duplicate_of.checksum_sha256
        ):
            errors['duplicate_of'] = 'Un duplicado exacto debe compartir checksum con el archivo canonico.'
        if errors:
            raise ValidationError(errors)
