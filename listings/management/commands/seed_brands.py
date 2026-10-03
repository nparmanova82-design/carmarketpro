from django.core.management.base import BaseCommand
from django.utils.text import slugify

from listings.models import Brand, CarModel

DATA = {
    "Chevrolet": ["Cobalt", "Gentra", "Malibu", "Spark", "Nexia", "Damas", "Tracker", "Captiva", "Onix"],
    "Toyota": ["Camry", "Corolla", "RAV4", "Land Cruiser", "Prado", "Highlander"],
    "Hyundai": ["Elantra", "Sonata", "Tucson", "Santa Fe", "Accent"],
    "Kia": ["K5", "Sportage", "Sorento", "Rio", "Cerato"],
    "BMW": ["3 Series", "5 Series", "X5", "X3", "7 Series"],
    "Mercedes-Benz": ["C-Class", "E-Class", "S-Class", "GLE", "GLC"],
    "BYD": ["Song Plus", "Han", "Seal", "Chazor", "Atto 3"],
    "Lada": ["Vesta", "Granta", "Niva"],
    "Volkswagen": ["Polo", "Passat", "Tiguan", "Golf"],
}


class Command(BaseCommand):
    help = "Заполняет справочник марок и моделей"

    def handle(self, *args, **options):
        created = 0
        for brand_name, models in DATA.items():
            brand, _ = Brand.objects.get_or_create(name=brand_name, defaults={"slug": slugify(brand_name)})
            for model_name in models:
                _, was_created = CarModel.objects.get_or_create(brand=brand, name=model_name)
                created += was_created
        self.stdout.write(self.style.SUCCESS(f"Готово: {len(DATA)} марок, добавлено моделей: {created}"))
