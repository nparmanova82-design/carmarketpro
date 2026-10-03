from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("brands", views.BrandViewSet, basename="brand")
router.register("models", views.CarModelViewSet, basename="carmodel")
router.register("listings", views.ListingViewSet, basename="listing")
router.register("comments", views.CommentViewSet, basename="comment")

urlpatterns = [
    path("favorites/", views.FavoriteListView.as_view(), name="favorites"),
    path("", include(router.urls)),
]
