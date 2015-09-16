# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.utils.timezone import utc
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('seafform', '0003_form_repoid'),
    ]

    operations = [
        migrations.AddField(
            model_name='form',
            name='creation_datetime',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2015, 9, 15, 8, 49, 18, 634121, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
