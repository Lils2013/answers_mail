from rest_framework import routers
from analytics.api.viewsets import TagViewSet, QuestionsViewSet


router = routers.DefaultRouter()
router.register(r'questions', QuestionsViewSet)
router.register(r'tags', TagViewSet)
