from django.db import migrations


def seed_default_regime(apps, schema_editor):
    RegimenTributarioEmpresa = apps.get_model('contabilidad', 'RegimenTributarioEmpresa')
    RegimenTributarioEmpresa.objects.get_or_create(
        codigo_regimen='EmpresaContabilidadCompletaV1',
        defaults={
            'descripcion': 'Regimen fiscal automatizable canonico del v1',
            'estado': 'activa',
        },
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('contabilidad', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_default_regime, noop_reverse),
    ]
