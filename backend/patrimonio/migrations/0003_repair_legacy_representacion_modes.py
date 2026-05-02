from django.db import migrations, models


def repair_legacy_representacion_modes(apps, schema_editor):
    ParticipacionPatrimonial = apps.get_model('patrimonio', 'ParticipacionPatrimonial')
    RepresentacionComunidad = apps.get_model('patrimonio', 'RepresentacionComunidad')

    migrated_rows = RepresentacionComunidad.objects.filter(
        observaciones='Migrado desde representante_socio legacy.',
    )

    for representacion in migrated_rows.iterator():
        is_participant = ParticipacionPatrimonial.objects.filter(
            comunidad_owner_id=representacion.comunidad_id,
            participante_socio_id=representacion.socio_representante_id,
            activo=True,
            vigente_desde__lte=representacion.vigente_desde,
        ).filter(
            models.Q(vigente_hasta__isnull=True) | models.Q(vigente_hasta__gte=representacion.vigente_desde)
        ).exists()
        expected_mode = 'participante_patrimonial' if is_participant else 'designado'
        if representacion.modo_representacion != expected_mode:
            representacion.modo_representacion = expected_mode
            representacion.save(update_fields=['modo_representacion', 'updated_at'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('patrimonio', '0002_participaciones_mixtas_y_representacion_comunidad'),
    ]

    operations = [
        migrations.RunPython(repair_legacy_representacion_modes, noop_reverse),
    ]
