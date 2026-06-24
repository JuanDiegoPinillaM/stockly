from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    tags=['Sistema'],
    summary='Estado de la API',
    responses={200: OpenApiResponse(inline_serializer(
        name='HealthResponse',
        fields={
            'status': serializers.CharField(),
            'service': serializers.CharField(),
            'message': serializers.CharField(),
        },
    ))},
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """Endpoint de prueba para verificar que la API responde."""
    return Response({
        'status': 'ok',
        'service': 'stockly-api',
        'message': 'La API de Stockly está funcionando.',
    })
