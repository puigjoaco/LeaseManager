from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contratos', '0011_periodocontractual_politica_base_renovacion_motivo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='entrega_llaves_autorizacion_motivo',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='contrato',
            name='entrega_llaves_autorizacion_ref',
            field=models.CharField(blank=True, default='', max_length=255),
            preserve_default=False,
        ),
    ]
