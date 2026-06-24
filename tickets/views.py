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

from .models import (
    Usuario, Sistema, Modulo, Documento, Prioridad, Estado, Categoria,
    Ticket, ChatterEntry, TicketTimeLog, ConocimientoEntry, Token
)
from tickets.authentication import TokenAuthentication

from .serializers import (
    UsuarioSerializer, UsuarioInputSerializer, UsuarioUpdateSerializer,
    SistemaSerializer, ModuloSerializer, DocumentoSerializer,
    PrioridadSerializer, EstadoSerializer, CategoriaSerializer,
    TicketSerializer, TicketInputSerializer, TicketUpdateSerializer,
    ChatterEntrySerializer, ChatterInputSerializer,
    TimeLogSerializer, ConocimientoSerializer,
)
from . import resend_email

# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────

@api_view(['POST'])
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

class ModuloViewSet(viewsets.ModelViewSet):
    queryset = Modulo.objects.select_related('sistema').prefetch_related('tickets').all()
    serializer_class = ModuloSerializer
    pagination_class = None

class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = Documento.objects.select_related('sistema', 'modulo').all()
    serializer_class = DocumentoSerializer
    pagination_class = None

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    pagination_class = None
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
    serializer_class = ConocimientoSerializer
    pagination_class = None

# ─────────────────────────────────────────────
#  REPORTES CORE
# ─────────────────────────────────────────────

@api_view(['GET'])
def reporte_resumen(request):
    total = Ticket.objects.count()
    return Response({'total_tickets': total, 'abiertos': Ticket.objects.filter(estado__es_estado_cierre=False).count()})

@api_view(['GET'])
def reporte_por_sistema(request):
    return Response([])

@api_view(['GET'])
def reporte_por_estado(request):
    return Response([])

@api_view(['GET'])
def reporte_por_prioridad(request):
    return Response([])

@api_view(['GET'])
def reporte_sla(request):
    return Response([])

@api_view(['GET'])
def reporte_tendencias(request):
    return Response([])

@api_view(['GET'])
def reporte_por_region(request):
    return Response([])

@api_view(['GET'])
def reporte_tickets(request):
    return Response([])

@api_view(['GET'])
def actividad_reciente(request):
    return Response([])

# ─────────────────────────────────────────────────────────────────
#  NUEVAS VISTAS DE COMPATIBILIDAD DESEMPAQUETADORAS (CRUD)
# ─────────────────────────────────────────────────────────────────

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_create_usuario(request):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = request.data
    serializer = UsuarioInputSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST', 'PUT', 'PATCH', 'GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_update_usuario(request, pk=None):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = request.data
    
    custom_data = payload.copy() if hasattr(payload, 'copy') else dict(payload)
    if 'estado' in custom_data:
        custom_data['activo'] = custom_data['estado'] in ['Activo', 'activo', True, 'true', 'True', 1, '1']

    usuario_id = pk or custom_data.get('id') or request.query_params.get('id')
    if not usuario_id:
        return Response({'detail': 'Falta el ID del usuario.'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        
    serializer = UsuarioSerializer(usuario, data=custom_data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_delete_usuario(request, pk=None):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = request.data
    usuario_id = pk or payload.get('id') or request.query_params.get('id')
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        usuario.delete()
        return Response({'detail': 'Usuario eliminado.'}, status=status.HTTP_200_OK)
    except Usuario.DoesNotExist:
        return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_create_ticket(request):
    payload = request.data.get('data') if 'data' in request.data else request.data
    serializer = TicketInputSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_create_modulo(request):
    payload = request.data.get('data') if 'data' in request.data else request.data
    serializer = ModuloSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_create_conocimiento(request):
    payload = request.data.get('data') if 'data' in request.data else request.data
    serializer = ConocimientoSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_chatter_list(request):
    ticket_id = request.query_params.get('ticket') or request.query_params.get('ticket_id')
    if ticket_id:
        entries = ChatterEntry.objects.filter(ticket_id=ticket_id).select_related('autor').order_by('fecha_creacion')
        return Response(ChatterEntrySerializer(entries, many=True).data)
    return Response([])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_timelogs_list(request):
    ticket_id = request.query_params.get('ticket') or request.query_params.get('ticket_id')
    if ticket_id:
        logs = TicketTimeLog.objects.filter(ticket_id=ticket_id).order_by('fecha_inicio')
        return Response(TimeLogSerializer(logs, many=True).data)
    return Response([])
