import csv
import logging

from django.core.management.base import BaseCommand

from foodgram import settings
from recipes.models import Ingredient


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, help='Path to file')

    def handle(self, *args, **options):
        with open(
                f'{settings.BASE_DIR}/data/ingredients.csv',
                'r',
                encoding='utf-8',
        ) as file:
            reader = csv.reader(file)

            for row in reader:
                name_csv = 0
                measurement_unit_csv = 1
                try:
                    _, created = Ingredient.objects.get_or_create(
                        name=row[name_csv],
                        measurement_unit=row[measurement_unit_csv],
                    )
                except Exception as error:
                    logging.exception(f'Ошибка в строке {row}: {error}')
