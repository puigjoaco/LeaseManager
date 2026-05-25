from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patrimonio', '0004_serviciopropiedad'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='representacioncomunidad',
            name='uniq_representacion_activa_por_comunidad',
        ),
    ]
