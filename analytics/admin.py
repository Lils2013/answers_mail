# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

# Register your models here.
from analytics.models import Question, Tag

admin.site.register(Question)
admin.site.register(Tag)
