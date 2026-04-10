from datetime import date

from django.db import migrations, models
import django.utils.timezone


def migrate_existing_representaciones(apps, schema_editor):
    ComunidadPatrimonial = apps.get_model('patrimonio', 'ComunidadPatrimonial')
    RepresentacionComunidad = apps.get_model('patrimonio', 'RepresentacionComunidad')

    for comunidad in ComunidadPatrimonial.objects.exclude(representante_socio__isnull=True):
        RepresentacionComunidad.objects.create(
            comunidad_id=comunidad.id,
            modo_representacion='participante_patrimonial',
            socio_representante_id=comunidad.representante_socio_id,
            vigente_desde=comunidad.created_at.date() if comunidad.created_at else date.today(),
            activo=True,
            observaciones='Migrado desde representante_socio legacy.',
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('patrimonio', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='participacionpatrimonial',
            old_name='socio',
            new_name='participante_socio',
        ),
        migrations.AlterField(
            model_name='participacionpatrimonial',
            name='participante_socio',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name='participaciones_patrimoniales_como_participante',
                to='patrimonio.socio',
            ),
        ),
        migrations.AddField(
            model_name='participacionpatrimonial',
            name='participante_empresa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name='participaciones_patrimoniales_como_participante',
                to='patrimonio.empresa',
            ),
        ),
        migrations.CreateModel(
            name='RepresentacionComunidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'modo_representacion',
                    models.CharField(
                        choices=[('participante_patrimonial', 'Participante patrimonial'), ('designado', 'Designado')],
                        default='participante_patrimonial',
                        max_length=32,
                    ),
                ),
                ('vigente_desde', models.DateField(default=django.utils.timezone.localdate)),
                ('vigente_hasta', models.DateField(blank=True, null=True)),
                ('activo', models.BooleanField(default=True)),
                ('observaciones', models.TextField(blank=True)),
                (
                    'comunidad',
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name='representaciones',
                        to='patrimonio.comunidadpatrimonial',
                    ),
                ),
                (
                    'socio_representante',
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name='representaciones_comunidad',
                        to='patrimonio.socio',
                    ),
                ),
            ],
            options={
                'ordering': ['comunidad_id', '-vigente_desde', '-id'],
            },
        ),
        migrations.RunPython(migrate_existing_representaciones, noop_reverse),
        migrations.RemoveField(
            model_name='comunidadpatrimonial',
            name='representante_socio',
        ),
        migrations.AddConstraint(
            model_name='participacionpatrimonial',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(participante_socio__isnull=False, participante_empresa__isnull=True)
                    | models.Q(participante_socio__isnull=True, participante_empresa__isnull=False)
                ),
                name='participacion_exactly_one_participant',
            ),
        ),
        migrations.AddConstraint(
            model_name='representacioncomunidad',
            constraint=models.UniqueConstraint(
                condition=models.Q(activo=True),
                fields=('comunidad',),
                name='uniq_representacion_activa_por_comunidad',
            ),
        ),
        migrations.AlterModelOptions(
            name='participacionpatrimonial',
            options={'ordering': ['-vigente_desde', '-id']},
        ),
    ]
