from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from .models import SiteConfig
from .permissions import IsAdminOrPublicRead
from .serializers import SiteConfigSerializer


class SiteConfigView(RetrieveUpdateAPIView):
    """GET público de la configuración del sitio; PATCH/PUT solo para admin.

    Siempre opera sobre el singleton (pk=1), así que no recibe id en la URL.
    """

    serializer_class = SiteConfigSerializer
    permission_classes = [IsAdminOrPublicRead]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return SiteConfig.load()
