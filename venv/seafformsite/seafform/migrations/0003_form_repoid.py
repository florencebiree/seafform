# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seafform', '0002_auto_20150913_2152'),
    ]

    operations = [
        migrations.AddField(
            model_name='form',
            name='repoid',
            field=models.CharField(default='', max_length=40),
            preserve_default=False,
        ),
    ]
