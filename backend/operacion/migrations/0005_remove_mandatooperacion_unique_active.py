from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operacion', '0004_mandatooperacion_autoridad_operativa_evidencia_ref_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='mandatooperacion',
            name='uniq_mandato_operacion_activo_por_propiedad',
        ),
    ]
