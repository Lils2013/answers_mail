from rest_framework import routers
from answers.viewsets import QuestionViewSet, TagViewSet

router = routers.DefaultRouter()
router.register(r'question', QuestionViewSet)
router.register(r'tag', TagViewSet)
