import django_filters

from .models import Listing


class ListingFilter(django_filters.FilterSet):
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    year_min = django_filters.NumberFilter(field_name="year", lookup_expr="gte")
    year_max = django_filters.NumberFilter(field_name="year", lookup_expr="lte")
    mileage_max = django_filters.NumberFilter(field_name="mileage", lookup_expr="lte")
    city = django_filters.CharFilter(lookup_expr="iexact")
    brand_slug = django_filters.CharFilter(field_name="brand__slug")
    has_photos = django_filters.BooleanFilter(method="filter_has_photos")

    class Meta:
        model = Listing
        fields = ("brand", "car_model", "fuel_type", "transmission", "body_type", "seller")

    def filter_has_photos(self, queryset, name, value):
        if value:
            return queryset.filter(photos__isnull=False).distinct()
        return queryset
