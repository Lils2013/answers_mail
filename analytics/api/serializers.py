# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from analytics.models import Tag, Question


class TagSerializer(ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    text = serializers.CharField(read_only=True)

    class Meta:
        model = Tag
        fields = '__all__'
        read_only_fields = ('id', 'text')


class QuestionSerializer(ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    text = serializers.CharField(read_only=True)

    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ('id', 'text')
