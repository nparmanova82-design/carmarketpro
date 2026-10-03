import hashlib
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, F, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .filters import ListingFilter
from .models import Brand, CarModel, Comment, Favorite, Listing, ListingPhoto, ListingView
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    MAX_PHOTOS,
    BrandSerializer,
    CarModelSerializer,
    CommentSerializer,
    FavoriteSerializer,
    ListingDetailSerializer,
    ListingListSerializer,
    ListingPhotoSerializer,
    ListingStatsSerializer,
    ListingWriteSerializer,
    PhotoUploadSerializer,
)


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.prefetch_related("models")
    serializer_class = BrandSerializer
    permission_classes = (permissions.AllowAny,)
    search_fields = ("name",)
    pagination_class = None


class CarModelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CarModel.objects.select_related("brand")
    serializer_class = CarModelSerializer
    permission_classes = (permissions.AllowAny,)
    filterset_fields = ("brand",)
    search_fields = ("name",)
    pagination_class = None


def visitor_key(request):
    if request.user.is_authenticated:
        return f"u:{request.user.pk}"
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
    ua = request.META.get("HTTP_USER_AGENT", "")
    return "a:" + hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:40]


class ListingViewSet(viewsets.ModelViewSet):
    """
    Объявления. Поиск: `?search=`; фильтры: brand, car_model, price_min/max,
    year_min/max, mileage_max, fuel_type, transmission, body_type, city, has_photos;
    сортировка: `?ordering=price|-price|year|-year|mileage|-created_at|-views_count`.
    """

    permission_classes = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly)
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filterset_class = ListingFilter
    search_fields = ("title", "brand__name", "car_model__name", "description", "city")
    ordering_fields = ("price", "year", "mileage", "created_at", "views_count")

    def get_queryset(self):
        user = self.request.user
        qs = Listing.objects.select_related("brand", "car_model", "seller").prefetch_related("photos")

        if self.action == "my":
            qs = qs.filter(seller=user)
        elif user.is_authenticated:
            qs = qs.filter(Q(is_active=True) | Q(seller=user))
        else:
            qs = qs.filter(is_active=True)

        if user.is_authenticated:
            qs = qs.annotate(is_favorite=Exists(Favorite.objects.filter(user=user, listing=OuterRef("pk"))))
        if self.action == "retrieve":
            qs = qs.annotate(
                favorites_count=Count("favorited_by", distinct=True),
                comments_count=Count("comments", distinct=True),
            )
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ListingWriteSerializer
        if self.action == "retrieve":
            return ListingDetailSerializer
        return ListingListSerializer

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        listing = self.get_object()
        if listing.seller_id != getattr(request.user, "pk", None):
            self._register_view(request, listing)
        return Response(self.get_serializer(listing).data)

    @staticmethod
    def _register_view(request, listing):
        try:
            with transaction.atomic():
                ListingView.objects.create(
                    listing=listing,
                    user=request.user if request.user.is_authenticated else None,
                    visitor_key=visitor_key(request),
                )
        except IntegrityError:
            return  # already counted today
        Listing.objects.filter(pk=listing.pk).update(views_count=F("views_count") + 1)
        listing.views_count += 1

    @extend_schema(summary="Мои объявления (включая неактивные)")
    @action(detail=False, permission_classes=[permissions.IsAuthenticated])
    def my(self, request):
        return self.list(request)

    @extend_schema(
        summary="Загрузить фотографии (multipart, поле images — несколько файлов)",
        request={"multipart/form-data": PhotoUploadSerializer},
        responses=ListingPhotoSerializer(many=True),
    )
    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def photos(self, request, pk=None):
        listing = self.get_object()
        serializer = PhotoUploadSerializer(data={"images": request.FILES.getlist("images")})
        serializer.is_valid(raise_exception=True)
        images = serializer.validated_data["images"]

        existing = listing.photos.count()
        if existing + len(images) > MAX_PHOTOS:
            raise ValidationError({"images": f"Максимум {MAX_PHOTOS} фото на объявление."})
        photos = ListingPhoto.objects.bulk_create(
            [ListingPhoto(listing=listing, image=img, order=existing + i) for i, img in enumerate(images)]
        )
        return Response(
            ListingPhotoSerializer(photos, many=True, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Удалить фотографию", responses={204: None})
    @action(detail=True, methods=["delete"], url_path=r"photos/(?P<photo_id>\d+)")
    def delete_photo(self, request, pk=None, photo_id=None):
        listing = self.get_object()
        photo = get_object_or_404(ListingPhoto, pk=photo_id, listing=listing)
        photo.image.delete(save=False)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Добавить (POST) / убрать (DELETE) из избранного",
        request=None,
        responses={201: OpenApiResponse(description="Добавлено"), 204: None},
    )
    @action(detail=True, methods=["post", "delete"], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        listing = self.get_object()
        if request.method == "POST":
            Favorite.objects.get_or_create(user=request.user, listing=listing)
            return Response({"is_favorite": True}, status=status.HTTP_201_CREATED)
        Favorite.objects.filter(user=request.user, listing=listing).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="Комментарии к объявлению", request=CommentSerializer, responses=CommentSerializer(many=True))
    @action(detail=True, methods=["get", "post"], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, pk=None):
        listing = self.get_object()
        if request.method == "POST":
            serializer = CommentSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save(listing=listing, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        qs = listing.comments.select_related("author")
        page = self.paginate_queryset(qs)
        serializer = CommentSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @extend_schema(summary="Статистика объявления (только владелец)", responses=ListingStatsSerializer)
    @action(detail=True, permission_classes=[permissions.IsAuthenticated])
    def stats(self, request, pk=None):
        listing = self.get_object()
        if listing.seller_id != request.user.pk and not request.user.is_staff:
            raise PermissionDenied("Статистика доступна только владельцу.")

        today = timezone.localdate()
        since = today - timedelta(days=29)
        records = listing.view_records
        by_day = dict(
            records.filter(date__gte=since).values("date").annotate(c=Count("id")).values_list("date", "c")
        )
        data = {
            "listing_id": listing.pk,
            "total_views": listing.views_count,
            "unique_views": records.values("visitor_key").distinct().count(),
            "views_today": by_day.get(today, 0),
            "favorites": listing.favorited_by.count(),
            "comments": listing.comments.count(),
            "chats": listing.conversations.count(),
            "views_by_day": [
                {"date": (since + timedelta(days=i)).isoformat(), "views": by_day.get(since + timedelta(days=i), 0)}
                for i in range(30)
            ],
        }
        return Response(ListingStatsSerializer(data).data)


class FavoriteListView(generics.ListAPIView):
    """Избранные объявления текущего пользователя."""

    serializer_class = FavoriteSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = ()

    def get_queryset(self):
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related("listing__brand", "listing__car_model")
            .prefetch_related("listing__photos")
        )


class CommentViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Редактирование/удаление своего комментария."""

    queryset = Comment.objects.select_related("author")
    serializer_class = CommentSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwnerOrReadOnly)
