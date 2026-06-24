import json
from pathlib import Path

from django.db import migrations

DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'colombia.json'


def seed(apps, schema_editor):
    Country = apps.get_model('geo', 'Country')
    Department = apps.get_model('geo', 'Department')
    City = apps.get_model('geo', 'City')

    data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    country, _ = Country.objects.get_or_create(
        code=data['code'], defaults={'name': data['country']}
    )

    for dep in data['departments']:
        department, _ = Department.objects.get_or_create(country=country, name=dep['name'])
        existing = set(department.cities.values_list('name', flat=True))
        new_cities = [
            City(department=department, name=name)
            for name in dep['cities']
            if name not in existing
        ]
        City.objects.bulk_create(new_cities, batch_size=500)


def unseed(apps, schema_editor):
    Country = apps.get_model('geo', 'Country')
    City = apps.get_model('geo', 'City')
    Department = apps.get_model('geo', 'Department')
    City.objects.all().delete()
    Department.objects.all().delete()
    Country.objects.filter(code='CO').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('geo', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
