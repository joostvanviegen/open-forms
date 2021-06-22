# Generated by Django 2.2.20 on 2021-06-14 13:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("config", "0007_globalconfiguration_display_sdk_information"),
    ]

    operations = [
        migrations.AddField(
            model_name="globalconfiguration",
            name="default_test_kvk",
            field=models.CharField(
                blank=True,
                default="",
                help_text="When provided, submissions that are started will have this KvK Number set as default for the session. Useful to test/demo prefill functionality.",
                max_length=9,
                verbose_name="default test KvK Number",
            ),
        ),
    ]