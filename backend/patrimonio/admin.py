from django.contrib import admin

from .models import ComunidadPatrimonial, Empresa, ParticipacionPatrimonial, Propiedad, RepresentacionComunidad, Socio


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'email', 'activo', 'updated_at')
    list_filter = ('activo',)
    search_fields = ('nombre', 'rut', 'email')


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('razon_social', 'rut', 'estado', 'updated_at')
    list_filter = ('estado',)
    search_fields = ('razon_social', 'rut')


@admin.register(ComunidadPatrimonial)
class ComunidadPatrimonialAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'representacion_actual', 'estado', 'updated_at')
    list_filter = ('estado',)
    search_fields = ('nombre',)

    def representacion_actual(self, obj):
        representacion = obj.representacion_vigente()
        if not representacion:
            return ''
        return f'{representacion.get_modo_representacion_display()}: {representacion.socio_representante.nombre}'


@admin.register(ParticipacionPatrimonial)
class ParticipacionPatrimonialAdmin(admin.ModelAdmin):
    list_display = ('participante_display', 'participante_tipo', 'owner_tipo', 'owner_id', 'porcentaje', 'activo', 'vigente_desde', 'vigente_hasta')
    list_filter = ('activo', 'empresa_owner', 'comunidad_owner')
    search_fields = ('participante_socio__nombre', 'participante_socio__rut', 'participante_empresa__razon_social', 'participante_empresa__rut')


@admin.register(RepresentacionComunidad)
class RepresentacionComunidadAdmin(admin.ModelAdmin):
    list_display = ('comunidad', 'modo_representacion', 'socio_representante', 'activo', 'vigente_desde', 'vigente_hasta')
    list_filter = ('modo_representacion', 'activo')
    search_fields = ('comunidad__nombre', 'socio_representante__nombre', 'socio_representante__rut')


@admin.register(Propiedad)
class PropiedadAdmin(admin.ModelAdmin):
    list_display = ('codigo_propiedad', 'direccion', 'comuna', 'tipo_inmueble', 'estado', 'owner_tipo')
    list_filter = ('estado', 'tipo_inmueble')
    search_fields = ('codigo_propiedad', 'direccion', 'comuna')
