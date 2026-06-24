from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import City, Country, Department
from .serializers import CitySerializer, CountrySerializer, DepartmentSerializer

GEO_TAG = ['Ubicaciones']


@extend_schema(tags=GEO_TAG, summary='Países (público)')
class CountryListView(generics.ListAPIView):
    queryset = Country.objects.filter(is_active=True)
    serializer_class = CountrySerializer
    permission_classes = [AllowAny]
    pagination_class = None


@extend_schema(
    tags=GEO_TAG,
    summary='Departamentos de un país (público)',
    parameters=[OpenApiParameter('country', int, description='ID del país')],
)
class DepartmentListView(generics.ListAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = Department.objects.filter(is_active=True)
        country = self.request.query_params.get('country')
        return qs.filter(country_id=country) if country else qs


@extend_schema(
    tags=GEO_TAG,
    summary='Ciudades de un departamento (público)',
    parameters=[OpenApiParameter('department', int, description='ID del departamento')],
)
class CityListView(generics.ListAPIView):
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = City.objects.filter(is_active=True)
        department = self.request.query_params.get('department')
        return qs.filter(department_id=department) if department else qs.none()
