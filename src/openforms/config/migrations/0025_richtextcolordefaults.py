# Generated by Django 3.2.13 on 2022-05-19 13:07
import colorsys
import re

from django.db import migrations

# default colors from CKEditor source code (in CSS HSL format)
# via https://github.com/ckeditor/ckeditor5/blob/master/packages/ckeditor5-font/src/fontcolor/fontcolorediting.js
default_cke_values = [
    {"color": "hsl(0, 0%, 0%)", "label": "Black"},
    {"color": "hsl(0, 0%, 30%)", "label": "Dim grey"},
    {"color": "hsl(0, 0%, 60%)", "label": "Grey"},
    {"color": "hsl(0, 0%, 90%)", "label": "Light grey"},
    {
        "color": "hsl(0, 0%, 100%)",
        "label": "White",
    },
    {"color": "hsl(0, 75%, 60%)", "label": "Red"},
    {"color": "hsl(30, 75%, 60%)", "label": "Orange"},
    {"color": "hsl(60, 75%, 60%)", "label": "Yellow"},
    {"color": "hsl(90, 75%, 60%)", "label": "Light green"},
    {"color": "hsl(120, 75%, 60%)", "label": "Green"},
    {"color": "hsl(150, 75%, 60%)", "label": "Aquamarine"},
    {"color": "hsl(180, 75%, 60%)", "label": "Turquoise"},
    {"color": "hsl(210, 75%, 60%)", "label": "Light blue"},
    {"color": "hsl(240, 75%, 60%)", "label": "Blue"},
    {"color": "hsl(270, 75%, 60%)", "label": "Purple"},
]


def hsl_to_rgbhex(hsl_css_color):
    exp = "^hsl\((\d+), (\d+)%, (\d+)%\)$"
    m = re.match(exp, hsl_css_color)
    if m:
        h = int(m.group(1))
        s = int(m.group(2))
        l = int(m.group(3))

        # conversion algorithm via https://stackoverflow.com/questions/41403936/converting-hsl-to-hex-in-python3
        rgb = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
        hex = "#%02x%02x%02x" % (
            round(rgb[0] * 255),
            round(rgb[1] * 255),
            round(rgb[2] * 255),
        )
        return hex


def add_colors(apps, schema_editor):
    RichTextColor = apps.get_model("config", "RichTextColor")

    for elem in default_cke_values:
        hex_color = hsl_to_rgbhex(elem["color"])
        if not hex_color:
            continue
        RichTextColor.objects.create(label=elem["label"], color=hex_color)


def remove_colors(apps, schema_editor):
    RichTextColor = apps.get_model("config", "RichTextColor")
    RichTextColor.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("config", "0024_richtextcolor"),
    ]

    operations = [
        migrations.RunPython(add_colors, reverse_code=remove_colors),
    ]