from django.urls import path

from .views import CityListView, CountryListView, DepartmentListView

urlpatterns = [
    path('geo/countries/', CountryListView.as_view(), name='geo-countries'),
    path('geo/departments/', DepartmentListView.as_view(), name='geo-departments'),
    path('geo/cities/', CityListView.as_view(), name='geo-cities'),
]
