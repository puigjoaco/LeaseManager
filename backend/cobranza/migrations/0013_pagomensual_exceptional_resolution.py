from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cobranza', '0012_pagomensual_effective_code_effect'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagomensual',
            name='resolucion_pago_excepcional_motivo',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='pagomensual',
            name='resolucion_pago_excepcional_ref',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
