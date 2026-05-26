from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cobranza', '0010_garantiacontractual_resolucion_exceso_garantia_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='valorufdiario',
            name='evidencia_ref',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='valorufdiario',
            name='motivo_carga',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='valorufdiario',
            name='responsable_ref',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
