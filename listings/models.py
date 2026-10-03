from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


def current_year():
    return timezone.now().year


class Brand(models.Model):
    name = models.CharField("марка", max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "марка"
        verbose_name_plural = "марки"

    def __str__(self):
        return self.name


class CarModel(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="models", verbose_name="марка")
    name = models.CharField("модель", max_length=100)

    class Meta:
        ordering = ("brand__name", "name")
        unique_together = ("brand", "name")
        verbose_name = "модель"
        verbose_name_plural = "модели"

    def __str__(self):
        return f"{self.brand.name} {self.name}"


class Listing(models.Model):
    class Fuel(models.TextChoices):
        PETROL = "petrol", "Бензин"
        DIESEL = "diesel", "Дизель"
        GAS = "gas", "Газ/метан"
        HYBRID = "hybrid", "Гибрид"
        ELECTRIC = "electric", "Электро"

    class Transmission(models.TextChoices):
        MANUAL = "manual", "Механика"
        AUTOMATIC = "automatic", "Автомат"
        ROBOT = "robot", "Робот"
        CVT = "cvt", "Вариатор"

    class Body(models.TextChoices):
        SEDAN = "sedan", "Седан"
        HATCHBACK = "hatchback", "Хэтчбек"
        SUV = "suv", "Внедорожник/кроссовер"
        WAGON = "wagon", "Универсал"
        COUPE = "coupe", "Купе"
        MINIVAN = "minivan", "Минивэн"
        PICKUP = "pickup", "Пикап"

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings", verbose_name="продавец"
    )
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="listings", verbose_name="марка")
    car_model = models.ForeignKey(CarModel, on_delete=models.PROTECT, related_name="listings", verbose_name="модель")
    title = models.CharField("заголовок", max_length=200, blank=True)
    year = models.PositiveIntegerField(
        "год", validators=[MinValueValidator(1950), MaxValueValidator(2100)]
    )
    price = models.DecimalField("цена, $", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    mileage = models.PositiveIntegerField("пробег, км")
    fuel_type = models.CharField("топливо", max_length=20, choices=Fuel.choices, default=Fuel.PETROL)
    transmission = models.CharField("КПП", max_length=20, choices=Transmission.choices, default=Transmission.MANUAL)
    body_type = models.CharField("кузов", max_length=20, choices=Body.choices, default=Body.SEDAN)
    engine_volume = models.DecimalField("объём двигателя, л", max_digits=3, decimal_places=1, null=True, blank=True)
    color = models.CharField("цвет", max_length=50, blank=True)
    city = models.CharField("город", max_length=100, blank=True)
    description = models.TextField("описание", blank=True)
    is_active = models.BooleanField("активно", default=True)
    views_count = models.PositiveIntegerField("просмотры", default=0, editable=False)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("обновлено", auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "объявление"
        verbose_name_plural = "объявления"
        indexes = [
            models.Index(fields=["price"]),
            models.Index(fields=["year"]),
            models.Index(fields=["is_active", "-created_at"]),
        ]

    def __str__(self):
        return self.title or f"{self.car_model} {self.year}"

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"{self.car_model} {self.year}"
        super().save(*args, **kwargs)


class ListingPhoto(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField("фото", upload_to="listings/%Y/%m/")
    order = models.PositiveSmallIntegerField("порядок", default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "фото"
        verbose_name_plural = "фотографии"


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [models.UniqueConstraint(fields=["user", "listing"], name="unique_favorite")]
        verbose_name = "избранное"
        verbose_name_plural = "избранное"


class Comment(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField("текст", max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "комментарий"
        verbose_name_plural = "комментарии"

    def __str__(self):
        return f"{self.author}: {self.text[:40]}"


class ListingView(models.Model):
    """Уникальный просмотр: один на посетителя (пользователь или IP) в день."""

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="view_records")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    visitor_key = models.CharField(max_length=64)
    date = models.DateField(default=timezone.localdate)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["listing", "visitor_key", "date"], name="unique_daily_view")
        ]
        verbose_name = "просмотр"
        verbose_name_plural = "просмотры"
