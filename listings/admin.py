from django.contrib import admin
from django.utils.html import format_html

from .models import Brand, CarModel, Comment, Favorite, Listing, ListingPhoto, ListingView


class CarModelInline(admin.TabularInline):
    model = CarModel
    extra = 1


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    inlines = [CarModelInline]


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ("name", "brand")
    list_filter = ("brand",)
    search_fields = ("name", "brand__name")


class ListingPhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 0
    readonly_fields = ("preview",)
    fields = ("preview", "image", "order")

    @admin.display(description="превью")
    def preview(self, obj):
        return format_html('<img src="{}" style="height:60px">', obj.image.url) if obj.image else "-"


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("author", "created_at")


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "seller", "year", "price", "mileage", "city", "is_active", "views_count", "created_at")
    list_filter = ("is_active", "brand", "fuel_type", "transmission", "body_type", "city")
    list_editable = ("is_active",)
    search_fields = ("title", "description", "seller__username", "brand__name", "car_model__name")
    autocomplete_fields = ("seller", "brand", "car_model")
    readonly_fields = ("views_count", "created_at", "updated_at")
    date_hierarchy = "created_at"
    inlines = [ListingPhotoInline, CommentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("listing", "author", "short_text", "created_at")
    search_fields = ("text", "author__username")

    @admin.display(description="текст")
    def short_text(self, obj):
        return obj.text[:60]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "listing", "created_at")


@admin.register(ListingView)
class ListingViewAdmin(admin.ModelAdmin):
    list_display = ("listing", "user", "date")
    list_filter = ("date",)
