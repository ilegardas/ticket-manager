from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.conf import settings
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.decorators import authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from datetime import timedelta, datetime

# Herramientas base de autenticación oficial
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import (
    Usuario, Sistema, Modulo, Documento, Prioridad, Estado, Categoria,
    Ticket, ChatterEntry, TicketTimeLog, ConocimientoEntry, Token
)

from .serializers import (
    UsuarioSerializer, UsuarioInputSerializer, UsuarioUpdateSerializer,
    SistemaSerializer, ModuloSerializer, DocumentoSerializer,
    PrioridadSerializer, EstadoSerializer, CategoriaSerializer,
    TicketSerializer, TicketInputSerializer, TicketUpdateSerializer,
    ChatterEntrySerializer, ChatterInputSerializer,
    TimeLogSerializer, ConocimientoSerializer,
)
from . import resend_email


# ─────────────────────────────────────────────────────────────────
# 🔴 CLASE DE AUTENTICACIÓN HÍBRIDA (SOPORTE PARA TOKEN / BEARER)
# ─────────────────────────────────────────────────────────────────
class TokenAuthentication(BaseAuthentication):
    """
    Clase de autenticación autocontenida que acepta los prefijos 'Token', 'Bearer'
    o la clave directa para compatibilidad absoluta con React en producción.
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) == 2:
            token_key = parts[1]
        elif len(parts) == 1:
            token_key = parts[0]
        else:
            return None

        try:
            token = Token.objects.select_related('usuario').get(key=token_key)
            if not token.usuario.activo:
                raise AuthenticationFailed('Usuario inactivo.')
            return (token.usuario, token)
        except Token.DoesNotExist:
            raise AuthenticationFailed('Token inválido.')


# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────

@api_view(['POST'])
@authentication_classes([])  # Limpio para la recepción inicial de credenciales
@permission_classes([AllowAny])
def login_view(request):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = {}

    correo = payload.get('correo_electronico') or payload.get('email') or payload.get('username')
    password = payload.get('password')
    
    if not correo or not password:
        return Response({'detail': 'Faltan credenciales obligatorias.'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        user = Usuario.objects.get(correo_electronico=correo)
        if not user.check_password(password):
            return Response({'detail': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)
    except Usuario.DoesNotExist:
        return Response({'detail': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.activo:
        return Response({'detail': 'El usuario se encuentra inactivo.'}, status=status.HTTP_403_FORBIDDEN)

    token, _ = Token.objects.get_or_create(usuario=user)
    return Response({
        'id': user.id,
        'correo_electronico': user.correo_electronico,
        'nombre_completo': user.nombre_completo,
        'rol': user.rol,
        'token': token.key,
    })

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout_view(request):
    Token.objects.filter(usuario=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def me_view(request):
    serializer = UsuarioSerializer(request.user)
    return Response(serializer.data)

# ─────────────────────────────────────────────
#  SLA GESTIÓN LOGS
# ─────────────────────────────────────────────

def _handle_state_change(ticket, old_estado, new_estado, user):
    now = timezone.now()
    if old_estado and old_estado.pausa_sla:
        open_log = TicketTimeLog.objects.filter(ticket=ticket, fecha_fin__isnull=True).first()
        if open_log:
            open_log.fecha_fin = now
            open_log.save()
            pause_minutes = sum(log.duracion_minutos for log in TicketTimeLog.objects.filter(ticket=ticket, duracion_minutos__isnull=False))
            ticket.tiempo_pausa_minutos = pause_minutes
            ticket.save(update_fields=['tiempo_pausa_minutos'])

    if new_estado and new_estado.pausa_sla:
        TicketTimeLog.objects.create(ticket=ticket, estado_pausa=new_estado.nombre, fecha_inicio=now)

    if new_estado and new_estado.es_estado_cierre:
        if not ticket.fecha_resolucion:
            ticket.fecha_resolucion = now
        ticket.fecha_cierre = now
        if ticket.fecha_creacion:
            delta = now - ticket.fecha_creacion
            ticket.tiempo_atencion_minutos = int(delta.total_seconds() / 60)
        ticket.save(update_fields=['fecha_resolucion', 'fecha_cierre', 'tiempo_atencion_minutos'])

    ChatterEntry.objects.create(
        ticket=ticket, tipo='cambio_estado', autor=user,
        estado_anterior=old_estado.nombre if old_estado else None,
        estado_nuevo=new_estado.nombre if new_estado else None,
        contenido=f"Estado cambiado de '{old_estado.nombre if old_estado else '—'}' a '{new_estado.nombre if new_estado else '—'}'"
    )

# ─────────────────────────────────────────────
#  VIEWSETS BASE
# ─────────────────────────────────────────────

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.select_related('sistema', 'modulo', 'prioridad', 'estado', 'categoria', 'usuario_reporta', 'usuario_asignado').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'prioridad', 'categoria', 'sistema', 'modulo', 'usuario_asignado', 'usuario_reporta']
    search_fields = ['folio', 'titulo', 'descripcion', 'codigo_error']
    ordering_fields = ['fecha_creacion', 'prioridad__orden', 'estado__orden']
    ordering = ['-fecha_creacion']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        data = request.data.get('data') if 'data' in request.data else request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        qs = super().get_queryset()
        vista = self.request.query_params.get('vista')
        if not vista or vista == 'todos': return qs
        now = timezone.now()
        if vista == 'abiertos': return qs.filter(estado__es_estado_cierre=False)
        if vista == 'en_proceso': return qs.filter(estado__es_estado_cierre=False, usuario_asignado__isnull=False)
        if vista == 'resueltos': return qs.filter(estado__es_estado_cierre=True, fecha_cierre__isnull=True)
        if vista == 'cerrados': return qs.filter(estado__es_estado_cierre=True)
        if vista == 'hoy': return qs.filter(fecha_creacion__date=now.date())
        return qs

    def get_serializer_class(self):
        if self.action == 'create': return TicketInputSerializer
        if self.action in ['partial_update', 'update']: return TicketUpdateSerializer
        return TicketSerializer

    def perform_create(self, serializer):
        ticket = serializer.save()
        estado = ticket.estado
        if estado and estado.pausa_sla:
            TicketTimeLog.objects.create(ticket=ticket, estado_pausa=estado.nombre, fecha_inicio=timezone.now())
        ChatterEntry.objects.create(ticket=ticket, tipo='sistema', contenido=f"Ticket creado con folio {ticket.folio}")

    def perform_update(self, serializer):
        old = self.get_object()
        old_estado = old.estado
        ticket = serializer.save()
        new_estado = ticket.estado
        if old_estado != new_estado:
            _handle_state_change(ticket, old_estado, new_estado, self.request.user if self.request.user.is_authenticated else None)

class SistemaViewSet(viewsets.ModelViewSet):
    queryset = Sistema.objects.prefetch_related('modulos', 'tickets').all()
    serializer_class = SistemaSerializer
    pagination_class = None
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

class ModuloViewSet(viewsets.ModelViewSet):
    queryset = Modulo.objects.select_related('sistema').prefetch_related('tickets').all()
    serializer_class = ModuloSerializer
    pagination_class = None
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = Documento.objects.select_related('sistema', 'modulo').all()
    serializer_class = DocumentoSerializer
    pagination_class = None
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    pagination_class = None
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get_serializer_class(self):
        if self.action == 'create': return UsuarioInputSerializer
        if self.action in ['partial_update', 'update']: return UsuarioUpdateSerializer
        return UsuarioSerializer

class PrioridadViewSet(viewsets.ModelViewSet):
    queryset = Prioridad.objects.all()
    serializer_class = PrioridadSerializer
    pagination_class = None

class EstadoViewSet(viewsets.ModelViewSet):
    queryset = Estado.objects.all()
    serializer_class = EstadoSerializer
    pagination_class = None

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    pagination_class = None

class ConocimientoViewSet(viewsets.ModelViewSet):
    queryset = ConocimientoEntry.objects.select_related('sistema', 'modulo').all()
    serializer_class = Conoc
