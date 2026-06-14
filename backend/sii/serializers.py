from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference
from core.scope_access import scope_queryset_for_user
from cobranza.models import PagoMensual

from patrimonio.models import Empresa

from .models import (
    AnnualEnterpriseRegisterMovement,
    AnnualEnterpriseRegisterSet,
    AnnualRealEstateItem,
    AnnualRealEstateSection,
    AnnualTaxArtifactMatrix,
    AnnualTaxArtifactMatrixItem,
    AnnualTaxDDJJFormLayout,
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxOfficialSource,
    AnnualTaxReviewChecklist,
    AnnualTaxSourceBundle,
    AnnualTaxTrialBalance,
    AnnualTaxTrialBalanceLine,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    DTEEmitido,
    EstadoAnnualTaxSourceBundle,
    F22PreparacionAnual,
    F29PreparacionMensual,
    MonthlyTaxFact,
    ProcesoRentaAnual,
    TaxCodeMapping,
    TaxYearRuleSet,
    TipoDTE,
    is_safe_public_sii_source_url,
)


def raise_drf_validation_error(error):
    if hasattr(error, 'message_dict'):
        raise serializers.ValidationError(error.message_dict)
    raise serializers.ValidationError(error.messages)


def build_validation_candidate(instance, model_class):
    if instance is None:
        return model_class()
    return model_class.objects.get(pk=instance.pk)


class RedactSensitiveSiiFieldsMixin:
    redacted_reference_fields = ()
    redacted_payload_fields = ()
    redacted_text_fields = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field_name in self.redacted_reference_fields:
            if field_name in data:
                data[field_name] = redact_sensitive_reference(data[field_name])
        for field_name in self.redacted_payload_fields:
            if field_name in data:
                data[field_name] = redact_sensitive_payload(data[field_name])
        for field_name in self.redacted_text_fields:
            if field_name in data:
                data[field_name] = redact_sensitive_reference(data[field_name])
        return data


class CapacidadTributariaSIISerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = (
        'certificado_ref',
        'evidencia_ref',
        'prueba_flujo_ref',
        'autorizacion_ambiente_ref',
        'regla_fiscal_ref',
    )
    redacted_payload_fields = ('ultimo_resultado',)

    class Meta:
        model = CapacidadTributariaSII
        fields = (
            'id',
            'empresa',
            'capacidad_key',
            'certificado_ref',
            'evidencia_ref',
            'prueba_flujo_ref',
            'autorizacion_ambiente_ref',
            'regla_fiscal_ref',
            'ambiente',
            'estado_gate',
            'ultimo_resultado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa'].queryset = scope_queryset_for_user(Empresa.objects.all(), user, company_paths=('id',))

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, CapacidadTributariaSII)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class TaxYearRuleSetSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('fuente_ref', 'responsable_aprobacion_ref')
    redacted_payload_fields = ('metadata',)

    class Meta:
        model = TaxYearRuleSet
        fields = (
            'id',
            'anio_tributario',
            'regimen_tributario',
            'version',
            'estado',
            'fuente_ref',
            'hash_normativo',
            'responsable_aprobacion_ref',
            'official_source',
            'descripcion',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, TaxYearRuleSet)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class TaxCodeMappingSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('formula_ref', 'evidencia_ref')
    redacted_payload_fields = ('metadata',)

    class Meta:
        model = TaxCodeMapping
        fields = (
            'id',
            'rule_set',
            'destino',
            'codigo_interno',
            'codigo_destino',
            'formula_ref',
            'evidencia_ref',
            'official_source',
            'estado',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, TaxCodeMapping)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class AnnualTaxOfficialSourceSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('source_ref', 'responsible_ref')
    redacted_payload_fields = ('metadata',)
    redacted_text_fields = ('scope_note',)

    class Meta:
        model = AnnualTaxOfficialSource
        fields = (
            'id',
            'anio_tributario',
            'source_key',
            'source_type',
            'title',
            'source_url',
            'source_ref',
            'source_hash',
            'retrieved_on',
            'responsible_ref',
            'estado',
            'applies_to',
            'form_code',
            'regime_code',
            'scope_note',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        source_url = data.get('source_url')
        if source_url and not is_safe_public_sii_source_url(source_url):
            data['source_url'] = '<redacted-sensitive-reference>'
        return data

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, AnnualTaxOfficialSource)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class AnnualTaxDDJJFormLayoutSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = (
        'resolution_ref',
        'layout_ref',
        'instructions_ref',
        'responsible_ref',
    )
    redacted_payload_fields = ('warnings', 'source_payload')

    class Meta:
        model = AnnualTaxDDJJFormLayout
        fields = (
            'id',
            'anio_tributario',
            'form_code',
            'title',
            'periodicidad',
            'allows_electronic_form',
            'allows_file_importer',
            'allows_file_upload',
            'allows_commercial_software',
            'allows_assistant',
            'medio_preferente',
            'due_date_label',
            'certificate_code',
            'certificate_due_label',
            'resolution_ref',
            'declaration_status',
            'layout_ref',
            'instructions_ref',
            'responsible_ref',
            'official_media_source',
            'official_form_source',
            'official_software_source',
            'warnings',
            'source_payload',
            'hash_layout',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_validators(self):
        # Model full_clean validates the conditional source/hash contract with instance context.
        return []

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, AnnualTaxDDJJFormLayout)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class AnnualTaxSourceBundleSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('source_label', 'authorization_ref', 'responsible_ref')
    redacted_payload_fields = ('resumen_fuentes',)

    class Meta:
        model = AnnualTaxSourceBundle
        fields = (
            'id',
            'empresa',
            'anio_tributario',
            'anio_comercial',
            'source_kind',
            'source_label',
            'authorization_ref',
            'responsible_ref',
            'hash_fuentes',
            'resumen_fuentes',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa'].queryset = scope_queryset_for_user(Empresa.objects.all(), user, company_paths=('id',))

    def get_validators(self):
        # Conditional unique constraints need the full instance; validate() delegates to model full_clean().
        return []

    def validate(self, attrs):
        if self.instance is not None and self.instance.estado == EstadoAnnualTaxSourceBundle.FROZEN:
            raise serializers.ValidationError(
                {'estado': 'AnnualTaxSourceBundle congelado no se modifica desde el endpoint generico.'}
            )
        candidate = build_validation_candidate(self.instance, AnnualTaxSourceBundle)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class MonthlyTaxFactSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('source_ref', 'responsible_ref')
    redacted_payload_fields = ('resumen_hecho',)

    class Meta:
        model = MonthlyTaxFact
        fields = (
            'id',
            'empresa',
            'anio',
            'mes',
            'cierre_mensual',
            'f29_preparacion',
            'liquidacion_mensual',
            'source_ref',
            'responsible_ref',
            'resumen_hecho',
            'hash_hecho',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa'].queryset = scope_queryset_for_user(Empresa.objects.all(), user, company_paths=('id',))

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, MonthlyTaxFact)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class AnnualTaxTrialBalanceSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('source_ref', 'responsible_ref')
    redacted_payload_fields = ('resumen_balance',)

    class Meta:
        model = AnnualTaxTrialBalance
        fields = (
            'id',
            'empresa',
            'proceso_renta_anual',
            'source_bundle',
            'rule_set',
            'official_source',
            'source_balance',
            'anio_tributario',
            'anio_comercial',
            'periodo_cierre',
            'source_ref',
            'responsible_ref',
            'lines_total',
            'warnings_total',
            'resumen_balance',
            'hash_balance',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualTaxTrialBalanceLineSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('formula_ref', 'evidencia_ref')
    redacted_payload_fields = ('warnings', 'source_payload')

    class Meta:
        model = AnnualTaxTrialBalanceLine
        fields = (
            'id',
            'trial_balance',
            'cuenta_contable',
            'codigo_cuenta',
            'nombre_cuenta',
            'clasificador_dj1847',
            'sumas_debe_clp',
            'sumas_haber_clp',
            'saldo_deudor_clp',
            'saldo_acreedor_clp',
            'inventario_activo_clp',
            'inventario_pasivo_clp',
            'resultado_perdida_clp',
            'resultado_ganancia_clp',
            'formula_ref',
            'evidencia_ref',
            'warnings',
            'source_payload',
            'hash_linea',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualTaxWorkbookSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('source_ref', 'responsible_ref')
    redacted_payload_fields = ('resumen_workbook',)

    class Meta:
        model = AnnualTaxWorkbook
        fields = (
            'id',
            'empresa',
            'proceso_renta_anual',
            'source_bundle',
            'rule_set',
            'anio_tributario',
            'anio_comercial',
            'tipo',
            'source_ref',
            'responsible_ref',
            'resumen_workbook',
            'hash_workbook',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualTaxWorkbookLineSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('formula_ref', 'evidencia_ref')
    redacted_payload_fields = ('warnings', 'source_payload')

    class Meta:
        model = AnnualTaxWorkbookLine
        fields = (
            'id',
            'workbook',
            'mapping',
            'codigo_interno',
            'codigo_destino',
            'origen',
            'signo',
            'monto_clp',
            'formula_ref',
            'evidencia_ref',
            'warnings',
            'source_payload',
            'hash_linea',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualEnterpriseRegisterSetSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('source_ref', 'responsible_ref')
    redacted_payload_fields = ('resumen_registro',)

    class Meta:
        model = AnnualEnterpriseRegisterSet
        fields = (
            'id',
            'empresa',
            'proceso_renta_anual',
            'source_bundle',
            'rule_set',
            'anio_tributario',
            'anio_comercial',
            'tipo_registro',
            'source_ref',
            'responsible_ref',
            'saldo_inicial_clp',
            'movimientos_total_clp',
            'saldo_final_clp',
            'resumen_registro',
            'hash_registro',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualEnterpriseRegisterMovementSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('formula_ref', 'evidencia_ref')
    redacted_payload_fields = ('warnings', 'source_payload')

    class Meta:
        model = AnnualEnterpriseRegisterMovement
        fields = (
            'id',
            'register_set',
            'source_workbook_line',
            'codigo_interno',
            'origen',
            'signo',
            'monto_clp',
            'formula_ref',
            'evidencia_ref',
            'warnings',
            'source_payload',
            'hash_movimiento',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualRealEstateSectionSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('source_ref', 'responsible_ref')
    redacted_payload_fields = ('resumen_seccion',)

    class Meta:
        model = AnnualRealEstateSection
        fields = (
            'id',
            'empresa',
            'proceso_renta_anual',
            'source_bundle',
            'rule_set',
            'official_contribution_source',
            'anio_tributario',
            'anio_comercial',
            'source_ref',
            'responsible_ref',
            'propiedades_total',
            'arriendo_devengado_total_clp',
            'arriendo_conciliado_total_clp',
            'arriendo_facturable_total_clp',
            'contribuciones_total_clp',
            'resumen_seccion',
            'hash_seccion',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualRealEstateItemSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('formula_ref', 'evidencia_ref')
    redacted_payload_fields = ('warnings', 'source_payload')

    class Meta:
        model = AnnualRealEstateItem
        fields = (
            'id',
            'section',
            'propiedad',
            'codigo_propiedad_snapshot',
            'rol_avaluo_snapshot',
            'direccion_snapshot',
            'comuna_snapshot',
            'region_snapshot',
            'tipo_inmueble_snapshot',
            'owner_tipo_snapshot',
            'owner_id_snapshot',
            'arriendo_devengado_clp',
            'arriendo_conciliado_clp',
            'arriendo_facturable_clp',
            'contribuciones_clp',
            'formula_ref',
            'evidencia_ref',
            'warnings',
            'source_payload',
            'hash_item',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualTaxArtifactMatrixSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('source_ref', 'responsible_ref')
    redacted_payload_fields = ('resumen_matriz',)

    class Meta:
        model = AnnualTaxArtifactMatrix
        fields = (
            'id',
            'empresa',
            'proceso_renta_anual',
            'source_bundle',
            'rule_set',
            'anio_tributario',
            'anio_comercial',
            'source_ref',
            'responsible_ref',
            'items_total',
            'ddjj_items_total',
            'f22_items_total',
            'resumen_matriz',
            'hash_matriz',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualTaxArtifactMatrixItemSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('formula_ref', 'evidencia_ref', 'responsible_ref')
    redacted_payload_fields = ('warnings', 'source_payload')

    class Meta:
        model = AnnualTaxArtifactMatrixItem
        fields = (
            'id',
            'matrix',
            'target_kind',
            'target_code',
            'medio_sii',
            'source_kind',
            'source_model',
            'source_object_id',
            'source_hash',
            'review_state',
            'formula_ref',
            'evidencia_ref',
            'responsible_ref',
            'warnings',
            'source_payload',
            'hash_item',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualTaxDossierSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('source_ref', 'responsible_ref', 'dossier_ref')
    redacted_payload_fields = ('resumen_dossier',)

    class Meta:
        model = AnnualTaxDossier
        fields = (
            'id',
            'empresa',
            'proceso_renta_anual',
            'source_bundle',
            'rule_set',
            'artifact_matrix',
            'anio_tributario',
            'anio_comercial',
            'source_ref',
            'responsible_ref',
            'dossier_ref',
            'review_state',
            'monthly_facts_total',
            'workbooks_total',
            'enterprise_registers_total',
            'real_estate_sections_total',
            'artifact_matrix_items_total',
            'warnings_total',
            'resumen_dossier',
            'hash_dossier',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualTaxExportSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('source_ref', 'responsible_ref', 'export_ref')
    redacted_payload_fields = ('export_payload',)

    class Meta:
        model = AnnualTaxExport
        fields = (
            'id',
            'empresa',
            'proceso_renta_anual',
            'dossier',
            'source_bundle',
            'rule_set',
            'artifact_matrix',
            'anio_tributario',
            'anio_comercial',
            'export_kind',
            'source_ref',
            'responsible_ref',
            'export_ref',
            'review_state',
            'target_items_total',
            'ddjj_items_total',
            'f22_items_total',
            'warnings_total',
            'official_format',
            'sii_submission',
            'final_tax_calculation',
            'export_payload',
            'hash_export',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualTaxReviewChecklistSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('checklist_ref', 'responsible_ref', 'evidence_ref')
    redacted_payload_fields = ('review_payload',)

    class Meta:
        model = AnnualTaxReviewChecklist
        fields = (
            'id',
            'empresa',
            'proceso_renta_anual',
            'dossier',
            'annual_export',
            'source_bundle',
            'rule_set',
            'artifact_matrix',
            'anio_tributario',
            'anio_comercial',
            'checklist_ref',
            'responsible_ref',
            'evidence_ref',
            'items_total',
            'completed_items_total',
            'blockers_total',
            'warnings_total',
            'review_payload',
            'hash_checklist',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class DTEEmitidoSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('sii_track_id',)
    redacted_text_fields = ('observaciones',)

    class Meta:
        model = DTEEmitido
        fields = (
            'id',
            'empresa',
            'capacidad_tributaria',
            'contrato',
            'pago_mensual',
            'distribucion_cobro_mensual',
            'arrendatario',
            'tipo_dte',
            'monto_neto_clp',
            'fecha_emision',
            'estado_dte',
            'sii_track_id',
            'ultimo_estado_sii',
            'observaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'empresa',
            'capacidad_tributaria',
            'contrato',
            'pago_mensual',
            'distribucion_cobro_mensual',
            'arrendatario',
            'monto_neto_clp',
            'fecha_emision',
            'created_at',
            'updated_at',
        )


class DTEGenerateSerializer(serializers.Serializer):
    pago_mensual_id = serializers.PrimaryKeyRelatedField(source='pago_mensual', queryset=PagoMensual.objects.all())
    tipo_dte = serializers.ChoiceField(
        choices=((TipoDTE.FACTURA_EXENTA, TipoDTE(TipoDTE.FACTURA_EXENTA).label),),
        required=False,
        default=TipoDTE.FACTURA_EXENTA,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['pago_mensual_id'].queryset = scope_queryset_for_user(
                PagoMensual.objects.all(),
                user,
                property_paths=('contrato__mandato_operacion__propiedad_id',),
            )


class DTEStatusSerializer(serializers.Serializer):
    estado_dte = serializers.ChoiceField(choices=DTEEmitido._meta.get_field('estado_dte').choices)
    sii_track_id = serializers.CharField(required=False, allow_blank=True)
    ultimo_estado_sii = serializers.CharField(required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class F29PreparacionMensualSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('borrador_ref', 'responsable_revision_ref')
    redacted_payload_fields = ('resumen_formulario',)
    redacted_text_fields = ('observaciones',)

    class Meta:
        model = F29PreparacionMensual
        fields = (
            'id',
            'empresa',
            'capacidad_tributaria',
            'cierre_mensual',
            'anio',
            'mes',
            'estado_preparacion',
            'resumen_formulario',
            'borrador_ref',
            'responsable_revision_ref',
            'observaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class F29GenerateSerializer(serializers.Serializer):
    empresa_id = serializers.PrimaryKeyRelatedField(source='empresa', queryset=Empresa.objects.all())
    anio = serializers.IntegerField(min_value=2000, max_value=9999)
    mes = serializers.IntegerField(min_value=1, max_value=12)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa_id'].queryset = scope_queryset_for_user(Empresa.objects.all(), user, company_paths=('id',))


class F29StatusSerializer(serializers.Serializer):
    estado_preparacion = serializers.ChoiceField(choices=F29PreparacionMensual._meta.get_field('estado_preparacion').choices)
    borrador_ref = serializers.CharField(required=False, allow_blank=True)
    responsable_revision_ref = serializers.CharField(required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class ProcesoRentaAnualSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('paquete_ddjj_ref', 'borrador_f22_ref', 'responsable_revision_ref')
    redacted_payload_fields = ('resumen_anual',)

    class Meta:
        model = ProcesoRentaAnual
        fields = (
            'id',
            'empresa',
            'anio_tributario',
            'estado',
            'source_bundle',
            'fecha_preparacion',
            'resumen_anual',
            'paquete_ddjj_ref',
            'borrador_f22_ref',
            'responsable_revision_ref',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class DDJJPreparacionAnualSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('paquete_ref', 'responsable_revision_ref')
    redacted_payload_fields = ('resumen_paquete',)
    redacted_text_fields = ('observaciones',)

    class Meta:
        model = DDJJPreparacionAnual
        fields = (
            'id',
            'empresa',
            'capacidad_tributaria',
            'proceso_renta_anual',
            'anio_tributario',
            'estado_preparacion',
            'resumen_paquete',
            'paquete_ref',
            'responsable_revision_ref',
            'observaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class F22PreparacionAnualSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('borrador_ref', 'responsable_revision_ref')
    redacted_payload_fields = ('resumen_f22',)
    redacted_text_fields = ('observaciones',)

    class Meta:
        model = F22PreparacionAnual
        fields = (
            'id',
            'empresa',
            'capacidad_tributaria',
            'proceso_renta_anual',
            'anio_tributario',
            'estado_preparacion',
            'resumen_f22',
            'borrador_ref',
            'responsable_revision_ref',
            'observaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualGenerateSerializer(serializers.Serializer):
    empresa_id = serializers.PrimaryKeyRelatedField(source='empresa', queryset=Empresa.objects.all())
    anio_tributario = serializers.IntegerField(min_value=2000, max_value=9999)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa_id'].queryset = scope_queryset_for_user(Empresa.objects.all(), user, company_paths=('id',))


class AnnualStatusSerializer(serializers.Serializer):
    estado_preparacion = serializers.ChoiceField(choices=F22PreparacionAnual._meta.get_field('estado_preparacion').choices)
    ref_value = serializers.CharField(required=False, allow_blank=True)
    responsable_revision_ref = serializers.CharField(required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)
