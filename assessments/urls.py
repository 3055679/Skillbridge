from django.urls import path
from . import views_take

app_name = "assessments"

urlpatterns = [
    path("take/<str:token>/", views_take.assessment_take, name="assessment_take"),
    path("submit/<str:token>/", views_take.assessment_submit, name="assessment_submit"),
]
