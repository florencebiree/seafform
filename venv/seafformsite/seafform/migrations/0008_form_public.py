# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seafform', '0007_auto_20150920_1410'),
    ]

    operations = [
        migrations.AddField(
            model_name='form',
            name='public',
            field=models.BooleanField(default=False),
        ),
    ]
