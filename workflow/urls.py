from django.urls import path

from .views import OverrideRequestCreateView

urlpatterns = [path("workflow/<str:cin>/override-requests/", OverrideRequestCreateView.as_view(), name="override-request")]
