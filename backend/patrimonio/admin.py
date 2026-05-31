from django.contrib import admin

from core.reference_validation import redact_sensitive_reference

from .models import (
    ComunidadPatrimonial,
    Empresa,
    ParticipacionPatrimonial,
    Propiedad,
    RepresentacionComunidad,
    ServicioPropiedad,
    Socio,
)


class ReadOnlyPatrimonyAdminMixin:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Socio)
class SocioAdmin(ReadOnlyPatrimonyAdminMixin, admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'email', 'activo', 'updated_at')
    list_filter = ('activo',)
    search_fields = ('nombre', 'rut', 'email')


@admin.register(Empresa)
class EmpresaAdmin(ReadOnlyPatrimonyAdminMixin, admin.ModelAdmin):
    list_display = ('razon_social', 'rut', 'estado', 'updated_at')
    list_filter = ('estado',)
    search_fields = ('razon_social', 'rut')


@admin.register(ComunidadPatrimonial)
class ComunidadPatrimonialAdmin(ReadOnlyPatrimonyAdminMixin, admin.ModelAdmin):
    list_display = ('nombre', 'representacion_actual', 'estado', 'updated_at')
    list_filter = ('estado',)
    search_fields = ('nombre',)

    def representacion_actual(self, obj):
        representacion = obj.representacion_vigente()
        if not representacion:
            return ''
        return f'{representacion.get_modo_representacion_display()}: {representacion.socio_representante.nombre}'


@admin.register(ParticipacionPatrimonial)
class ParticipacionPatrimonialAdmin(ReadOnlyPatrimonyAdminMixin, admin.ModelAdmin):
    list_display = ('participante_display', 'participante_tipo', 'owner_tipo', 'owner_id', 'porcentaje', 'activo', 'vigente_desde', 'vigente_hasta')
    list_filter = ('activo', 'empresa_owner', 'comunidad_owner')
    search_fields = ('participante_socio__nombre', 'participante_socio__rut', 'participante_empresa__razon_social', 'participante_empresa__rut')


@admin.register(RepresentacionComunidad)
class RepresentacionComunidadAdmin(ReadOnlyPatrimonyAdminMixin, admin.ModelAdmin):
    list_display = (
        'comunidad',
        'modo_representacion',
        'socio_representante',
        'activo',
        'vigente_desde',
        'vigente_hasta',
        'evidencia_ref_redacted',
    )
    list_filter = ('modo_representacion', 'activo')
    search_fields = ('comunidad__nombre', 'socio_representante__nombre', 'socio_representante__rut')
    fields = (
        'comunidad',
        'modo_representacion',
        'socio_representante',
        'activo',
        'vigente_desde',
        'vigente_hasta',
        'evidencia_ref_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('evidencia_ref_redacted', 'created_at', 'updated_at')

    def evidencia_ref_redacted(self, obj):
        return redact_sensitive_reference(obj.evidencia_ref) or ''


@admin.register(Propiedad)
class PropiedadAdmin(ReadOnlyPatrimonyAdminMixin, admin.ModelAdmin):
    list_display = ('codigo_propiedad', 'direccion', 'comuna', 'tipo_inmueble', 'estado', 'owner_tipo')
    list_filter = ('estado', 'tipo_inmueble')
    search_fields = ('codigo_propiedad', 'direccion', 'comuna')


@admin.register(ServicioPropiedad)
class ServicioPropiedadAdmin(ReadOnlyPatrimonyAdminMixin, admin.ModelAdmin):
    list_display = (
        'propiedad',
        'tipo_servicio',
        'proveedor_nombre',
        'numero_cliente',
        'activo',
        'evidencia_ref_redacted',
    )
    list_filter = ('tipo_servicio', 'activo')
    search_fields = ('propiedad__codigo_propiedad', 'proveedor_nombre', 'numero_cliente', 'administrador_nombre')
    fields = (
        'propiedad',
        'tipo_servicio',
        'proveedor_nombre',
        'numero_cliente',
        'administrador_nombre',
        'activo',
        'evidencia_ref_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('evidencia_ref_redacted', 'created_at', 'updated_at')

    def evidencia_ref_redacted(self, obj):
        return redact_sensitive_reference(obj.evidencia_ref) or ''
