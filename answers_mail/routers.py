from rest_framework import routers
from answers.viewsets import QuestionViewSet
from analytics.api.viewsets import TagViewSet, QuestionsViewSet


router = routers.DefaultRouter()
router.register(r'question', QuestionViewSet)
router.register(r'questions', QuestionsViewSet)
router.register(r'tags', TagViewSet)
