# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from analytics.models import Tag, Question, Category


class TagSerializer(ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    text = serializers.CharField(read_only=True)

    class Meta:
        model = Tag
        fields = ('id', 'text', 'questions_count')
        read_only_fields = ('id', 'text')


class QuestionSerializer(ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    text = serializers.CharField(read_only=True)

    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ('id', 'text')


class CategorySerializer(ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)

    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ('id', 'name')


class GraphSerializer(serializers.Serializer):
    date = serializers.IntegerField(read_only=True)
    count = serializers.IntegerField(read_only=True)
