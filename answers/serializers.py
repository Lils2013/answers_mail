from rest_framework import serializers

from answers.models import Question, Tag


class QuestionSerializer (serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class TagSerializer (serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'
