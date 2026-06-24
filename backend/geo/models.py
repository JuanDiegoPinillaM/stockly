from django.db import models


class Country(models.Model):
    """País. Por ahora solo Colombia, pero el modelo soporta más."""

    name = models.CharField('nombre', max_length=120, unique=True)
    code = models.CharField('código ISO', max_length=2, unique=True)
    is_active = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'país'
        verbose_name_plural = 'países'
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    """Departamento (o estado) de un país."""

    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name='departments', verbose_name='país'
    )
    name = models.CharField('nombre', max_length=120)
    is_active = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'departamento'
        verbose_name_plural = 'departamentos'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['country', 'name'], name='unique_department_per_country'
            )
        ]

    def __str__(self):
        return self.name


class City(models.Model):
    """Ciudad (o municipio) de un departamento."""

    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='cities', verbose_name='departamento'
    )
    name = models.CharField('nombre', max_length=160)
    is_active = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'ciudad'
        verbose_name_plural = 'ciudades'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['department', 'name'], name='unique_city_per_department'
            )
        ]

    def __str__(self):
        return self.name
