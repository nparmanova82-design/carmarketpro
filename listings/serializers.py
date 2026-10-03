from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from users.serializers import PublicUserSerializer

from .models import Brand, CarModel, Comment, Favorite, Listing, ListingPhoto

MAX_PHOTOS = 20


class CarModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarModel
        fields = ("id", "brand", "name")


class BrandSerializer(serializers.ModelSerializer):
    models = CarModelSerializer(many=True, read_only=True)

    class Meta:
        model = Brand
        fields = ("id", "name", "slug", "models")


class ListingPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingPhoto
        fields = ("id", "image", "order")


class PhotoUploadSerializer(serializers.Serializer):
    images = serializers.ListField(child=serializers.ImageField(), allow_empty=False, max_length=MAX_PHOTOS)


class ListingListSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    model_name = serializers.CharField(source="car_model.name", read_only=True)
    main_photo = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = (
            "id", "title", "brand", "brand_name", "car_model", "model_name",
            "year", "price", "mileage", "fuel_type", "transmission", "body_type",
            "city", "main_photo", "is_favorite", "views_count", "created_at",
        )

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_main_photo(self, obj):
        photos = list(obj.photos.all())
        if not photos:
            return None
        request = self.context.get("request")
        url = photos[0].image.url
        return request.build_absolute_uri(url) if request else url

    def get_is_favorite(self, obj) -> bool:
        return getattr(obj, "is_favorite", False)


class ListingDetailSerializer(ListingListSerializer):
    seller = PublicUserSerializer(read_only=True)
    photos = ListingPhotoSerializer(many=True, read_only=True)
    favorites_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta(ListingListSerializer.Meta):
        fields = ListingListSerializer.Meta.fields + (
            "seller", "engine_volume", "color", "description", "is_active",
            "photos", "favorites_count", "comments_count", "updated_at",
        )


class ListingWriteSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False, max_length=MAX_PHOTOS
    )

    class Meta:
        model = Listing
        fields = (
            "id", "brand", "car_model", "title", "year", "price", "mileage",
            "fuel_type", "transmission", "body_type", "engine_volume", "color",
            "city", "description", "is_active", "images",
        )
        # multipart forms omit unchecked booleans; keep new listings active by default
        extra_kwargs = {"is_active": {"default": True}}

    def validate(self, attrs):
        brand = attrs.get("brand", getattr(self.instance, "brand", None))
        car_model = attrs.get("car_model", getattr(self.instance, "car_model", None))
        if brand and car_model and car_model.brand_id != brand.id:
            raise serializers.ValidationError({"car_model": "Модель не принадлежит выбранной марке."})
        return attrs

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        listing = Listing.objects.create(**validated_data)
        ListingPhoto.objects.bulk_create(
            [ListingPhoto(listing=listing, image=img, order=i) for i, img in enumerate(images)]
        )
        return listing

    def update(self, instance, validated_data):
        validated_data.pop("images", None)  # photos are managed via /photos/
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return ListingDetailSerializer(instance, context=self.context).data


class CommentSerializer(serializers.ModelSerializer):
    author = PublicUserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "listing", "author", "text", "created_at")
        read_only_fields = ("listing",)


class FavoriteSerializer(serializers.ModelSerializer):
    listing = ListingListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "listing", "created_at")


class ListingStatsSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField()
    total_views = serializers.IntegerField()
    unique_views = serializers.IntegerField()
    views_today = serializers.IntegerField()
    favorites = serializers.IntegerField()
    comments = serializers.IntegerField()
    chats = serializers.IntegerField()
    views_by_day = serializers.ListField(child=serializers.DictField())
