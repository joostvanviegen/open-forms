# Generated by Django 3.2.12 on 2022-04-08 14:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('irma', '0003_rename__service_irmaconfig_service'),
    ]

    operations = [
        migrations.RenameField(
            model_name='irmaconfig',
            old_name='service',
            new_name='_service',
        ),
    ]