from django.contrib import admin

from core.reference_validation import redact_sensitive_reference

from .models import AsignacionCanalOperacion, CuentaRecaudadora, IdentidadDeEnvio, MandatoOperacion


@admin.register(CuentaRecaudadora)
class CuentaRecaudadoraAdmin(admin.ModelAdmin):
    list_display = ('institucion', 'numero_cuenta', 'owner_tipo', 'owner_display', 'modo_operativo', 'estado_operativo')
    list_filter = ('estado_operativo', 'modo_operativo', 'moneda_operativa', 'institucion')
    search_fields = ('institucion', 'numero_cuenta', 'titular_nombre', 'titular_rut')
    fields = (
        'empresa_owner',
        'comunidad_owner',
        'socio_owner',
        'institucion',
        'numero_cuenta',
        'tipo_cuenta',
        'titular_nombre',
        'titular_rut',
        'moneda_operativa',
        'uso_operativo',
        'modo_operativo',
        'evidencia_operativa_ref_redacted',
        'estado_operativo',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('evidencia_operativa_ref_redacted', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def evidencia_operativa_ref_redacted(self, obj):
        return redact_sensitive_reference(obj.evidencia_operativa_ref) or ''


@admin.register(IdentidadDeEnvio)
class IdentidadDeEnvioAdmin(admin.ModelAdmin):
    list_display = ('canal', 'remitente_visible', 'direccion_o_numero', 'owner_tipo', 'owner_display', 'estado')
    list_filter = ('canal', 'estado')
    search_fields = ('remitente_visible', 'direccion_o_numero')
    fields = (
        'empresa_owner',
        'socio_owner',
        'canal',
        'remitente_visible',
        'direccion_o_numero',
        'credencial_ref_redacted',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('credencial_ref_redacted', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def credencial_ref_redacted(self, obj):
        return redact_sensitive_reference(obj.credencial_ref) or ''


@admin.register(MandatoOperacion)
class MandatoOperacionAdmin(admin.ModelAdmin):
    list_display = (
        'propiedad',
        'propietario_tipo',
        'administrador_operativo_tipo',
        'recaudador_tipo',
        'autoridad_operativa_nombre',
        'cuenta_recaudadora',
        'estado',
        'vigencia_desde',
    )
    list_filter = ('estado', 'tipo_relacion_operativa')
    search_fields = (
        'propiedad__codigo_propiedad',
        'propiedad__direccion',
        'tipo_relacion_operativa',
        'autoridad_operativa_nombre',
        'autoridad_operativa_rut',
    )
    fields = (
        'propiedad',
        'propietario_empresa_owner',
        'propietario_comunidad_owner',
        'propietario_socio_owner',
        'administrador_empresa_owner',
        'administrador_socio_owner',
        'recaudador_empresa_owner',
        'recaudador_comunidad_owner',
        'recaudador_socio_owner',
        'entidad_facturadora',
        'cuenta_recaudadora',
        'tipo_relacion_operativa',
        'autoriza_recaudacion',
        'autoriza_facturacion',
        'autoriza_comunicacion',
        'autoridad_operativa_nombre',
        'autoridad_operativa_rut',
        'autoridad_operativa_evidencia_ref_redacted',
        'vigencia_desde',
        'vigencia_hasta',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('autoridad_operativa_evidencia_ref_redacted', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def autoridad_operativa_evidencia_ref_redacted(self, obj):
        return redact_sensitive_reference(obj.autoridad_operativa_evidencia_ref) or ''


@admin.register(AsignacionCanalOperacion)
class AsignacionCanalOperacionAdmin(admin.ModelAdmin):
    list_display = ('mandato_operacion', 'canal', 'identidad_envio', 'prioridad', 'estado')
    list_filter = ('canal', 'estado')
    search_fields = ('mandato_operacion__propiedad__codigo_propiedad', 'identidad_envio__direccion_o_numero')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
