from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from structlog import get_logger

from katalogus.models import Boefje
from katalogus.serializers import BoefjeSerializer

logger = get_logger(__name__)


class BoefjeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BoefjeSerializer
    queryset = Boefje.objects.all()
