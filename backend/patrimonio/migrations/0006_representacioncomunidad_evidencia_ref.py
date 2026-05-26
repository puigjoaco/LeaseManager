from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patrimonio', '0005_remove_representacioncomunidad_unique_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='representacioncomunidad',
            name='evidencia_ref',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
