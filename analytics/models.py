# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.conf import settings
# Create your models here.


class Category(models.Model):
    name = models.TextField()
    questions_count = models.IntegerField(default=None, blank=True, null=True)


class Question(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=False)
    rating = models.IntegerField(default=None, blank=True, null=True)
    poll_type = models.IntegerField(default=None, blank=True, null=True)
    category = models.ForeignKey(Category, related_name='questions', default=None, blank=True, null=True)
    parent_category = models.ForeignKey(Category, related_name='questions_parent', default=None, blank=True, null=True)

    def __unicode__(self):
        result = '{0} {1}'.format(
            self.created_at.ctime(),
            self.text[:30])
        return result

    # class Meta:
    #     ordering = ['created_at']


class Tag(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    questions = models.ManyToManyField(Question)
    questions_count = models.IntegerField(default=None, blank=True, null=True)
    global_idf = models.FloatField(default=None, blank=True, null=True)

    #
    # def __unicode__(self):
    #     result = '{0} {1}'.format(
    #         self.created_at.ctime(),
    #         self.text[:30])
    #     return result

    # class Meta:
    #     ordering = ['created_at']


class Counter(models.Model):
    datetime = models.DateTimeField(auto_now_add=False)
    tag = models.ForeignKey(Tag, related_name='counters')
    category = models.ForeignKey(Category)
    count = models.IntegerField()


class GlobalCounter(models.Model):  # счетчик слово-категория, только за все время
    tag = models.ForeignKey(Tag)  #
    category = models.ForeignKey(Category)  #
    count = models.IntegerField()  # считаем все вхождения слова в вопросы категории
    local_idf = models.FloatField()
