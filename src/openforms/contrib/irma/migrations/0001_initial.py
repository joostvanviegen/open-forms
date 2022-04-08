# Generated by Django 3.2.12 on 2022-04-07 13:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('zgw_consumers', '0015_auto_20220307_1522'),
    ]

    operations = [
        migrations.CreateModel(
            name='IrmaConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('irma_service', models.OneToOneField(limit_choices_to={'api_type': 'orc'}, null=True, on_delete=django.db.models.deletion.SET_NULL, to='zgw_consumers.service', verbose_name='Irma API')),
            ],
            options={
                'verbose_name': 'Irma configuration',
            },
        ),
    ]
