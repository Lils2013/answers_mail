from rest_framework import routers
from answers.viewsets import QuestionViewSet


router = routers.DefaultRouter()
router.register(r'question', QuestionViewSet)
