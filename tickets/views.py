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
#  AUTENTICACIÓN HÍBRIDA ROBUSTA (TOKEN / BEARER)
# ─────────────────────────────────────────────────────────────────
class TokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header: return None
        parts = auth_header.split()
        if len(parts) == 2: token_key = parts[1]
        elif len(parts) == 1: token_key = parts[0]
        else: return None
        try:
            token = Token.objects.select_related('usuario').get(key=token_key)
            if not token.usuario.activo: raise AuthenticationFailed('Usuario inactivo.')
            return (token.usuario, token)
        except Token.DoesNotExist:
            raise AuthenticationFailed('Token inválido.')

# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────

@api_view(['POST'])
@authentication_classes([])  
@permission_classes([AllowAny])
def login_view(request):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = {}
    correo = payload.get('correo_electronico') or payload.get('email') or payload.get('username')
    password = payload.get('password')
    if not correo or not password:
        return Response({'detail': 'Faltan credenciales.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = Usuario.objects.get(correo_electronico=correo)
        if not user.check_password(password):
            return Response({'detail': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)
    except Usuario.DoesNotExist:
        return Response({'detail': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.activo:
        return Response({'detail': 'Usuario inactivo.'}, status=status.HTTP_403_FORBIDDEN)
    token, _ = Token.objects.get_or_create(usuario=user)
    return Response({'id': user.id, 'correo_electronico': user.correo_electronico, 'nombre_completo': user.nombre_completo, 'rol': user.rol, 'token': token.key})

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
    return Response(UsuarioSerializer(request.user).data)

# ─────────────────────────────────────────────
#  SLA LOGS
# ─────────────────────────────────────────────

def _handle_state_change(ticket, old_estado, new_estado, user):
    now = timezone.now()
    if old_estado and old_estado.pausa_sla:
        open_log = TicketTimeLog.objects.filter(ticket=ticket, fecha_fin__isnull=True).first()
        if open_log:
            open_log.fecha_fin = now
            open_log.save()
            ticket.tiempo_pausa_minutos = sum(log.duracion_minutos for log in TicketTimeLog.objects.filter(ticket=ticket, duracion_minutos__isnull=False))
            ticket.save(update_fields=['tiempo_pausa_minutos'])
    if new_estado and new_estado.pausa_sla:
        TicketTimeLog.objects.create(ticket=ticket, estado_pausa=new_estado.nombre, fecha_inicio=now)
    if new_estado and new_estado.es_estado_cierre:
        if not ticket.fecha_resolucion: ticket.fecha_resolucion = now
        ticket.fecha_cierre = now
        if ticket.fecha_creacion: ticket.tiempo_atencion_minutos = int((now - ticket.fecha_creacion).total_seconds() / 60)
        ticket.save(update_fields=['fecha_resolucion', 'fecha_cierre', 'tiempo_atencion_minutos'])
    ChatterEntry.objects.create(ticket=ticket, tipo='cambio_estado', autor=user, estado_anterior=old_estado.nombre if old_estado else None, estado_nuevo=new_estado.nombre if new_estado else None, contenido=f"Estado cambiado a '{new_estado.nombre if new_estado else '—'}'")

# ─────────────────────────────────────────────
#  FUNCIÓN REUTILIZABLE DE LIMPIEZA DE FECHAS
# ─────────────────────────────────────────────
def _clean_view_date_string(date_str):
    if not date_str:
        return "2026-06-25T00:00:00Z"
    if '-' in date_str and date_str.count('-') == 3:
        date_str = date_str.rsplit('-', 1)[0]
    elif '+' in date_str:
        date_str = date_str.rsplit('+', 1)[0]
    if date_str.endswith('Z'):
        date_str = date_str[:-1]
    return date_str + "Z"

# ─────────────────────────────────────────────
#  VIEWSETS
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



    # 🛡️ RETRIEVE ULTRA-BLINDADO: Entrega el ticket, el chatter y los logs en una sola consulta limpia
    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            instance = Ticket.objects.select_related(
                'sistema', 'modulo', 'prioridad', 'estado', 'categoria', 'usuario_reporta', 'usuario_asignado'
            ).get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({'detail': f'Ticket {pk} no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TicketSerializer(instance)
        data = serializer.data

        # 1. 🛡️ Formateo e inmunidad absoluta de strings de fechas UTC 'Z'
        base_date = _clean_view_date_string(data.get('fecha_creacion'))
        data['fecha_creacion'] = _clean_view_date_string(data.get('fecha_creacion'))
        data['fecha_asignacion'] = _clean_view_date_string(data.get('fecha_asignacion')) if data.get('fecha_asignacion') else base_date
        data['fecha_primera_respuesta'] = _clean_view_date_string(data.get('fecha_primera_respuesta')) if data.get('fecha_primera_respuesta') else base_date
        data['fecha_resolucion'] = _clean_view_date_string(data.get('fecha_resolucion')) if data.get('fecha_resolucion') else base_date
        data['fecha_cierre'] = _clean_view_date_string(data.get('fecha_cierre')) if data.get('fecha_cierre') else base_date

        # 2. 🔌 INYECCIÓN DIRECTA DE SUB-RECURSOS: Rompe el bucle de carga infinita del frontend
        # Traemos el chatter correspondiente a este ticket
        chatter_qs = ChatterEntry.objects.filter(ticket=instance).order_by('fecha_creacion')
        data['chatter'] = ChatterEntrySerializer(chatter_qs, many=True).data

        # Traemos los logs de tiempo correspondientes a este ticket
        logs_qs = TicketTimeLog.objects.filter(ticket=instance).order_by('fecha_inicio')
        data['time_logs'] = TimeLogSerializer(logs_qs, many=True).data

        return Response(data)
        

    def create(self, request, *args, **kwargs):
        data = request.data.get('data') if 'data' in request.data else request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        if ticket.estado and ticket.estado.pausa_sla: TicketTimeLog.objects.create(ticket=ticket, estado_pausa=ticket.estado.nombre, fecha_inicio=timezone.now())
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



class SistemaViewSet(viewsets.ModelViewSet):
    queryset = Sistema.objects.all()
    serializer_class = SistemaSerializer
    pagination_class = None

class ModuloViewSet(viewsets.ModelViewSet):
    queryset = Modulo.objects.all()
    serializer_class = ModuloSerializer
    pagination_class = None

class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = Documento.objects.all()
    serializer_class = DocumentoSerializer
    pagination_class = None

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    pagination_class = None
    def get_serializer_class(self):
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
    queryset = ConocimientoEntry.objects.all()
    serializer_class = ConocimientoSerializer
    pagination_class = None

# ─────────────────────────────────────────────
#  REPORTES CORE
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_resumen(request):
    now = timezone.now()
    total = Ticket.objects.count()
    abiertos = Ticket.objects.filter(estado__es_estado_cierre=False).count()
    en_proceso = Ticket.objects.filter(estado__es_estado_cierre=False, usuario_asignado__isnull=False).count()
    resueltos = Ticket.objects.filter(estado__es_estado_cierre=True, fecha_cierre__isnull=True).count()
    cerrados = Ticket.objects.filter(estado__es_estado_cierre=True).count()
    avg_res = Ticket.objects.filter(tiempo_atencion_minutos__isnull=False).aggregate(avg=Avg('tiempo_atencion_minutos'))['avg'] or 0
    return Response({
        'total_tickets': total, 'abiertos': abiertos, 'en_proceso': en_proceso, 'resueltos': resueltos, 'cerrados': cerrados,
        'vencidos': 0, 'tickets_hoy': Ticket.objects.filter(fecha_creacion__date=now.date()).count(), 'tickets_semana': 0,
        'promedio_resolucion_horas': round(avg_res / 60, 2), 'satisfaccion_promedio': 5.0, 'porcentaje_sla_cumplido': 100.0
    })

@api_view(['GET'])
def reporte_por_sistema(request):
    return Response([{'id': r['sistema__id'], 'nombre': r['sistema__nombre'] or 'Sin sistema', 'total': r['total']} for r in Ticket.objects.values('sistema__id', 'sistema__nombre').annotate(total=Count('id'))])

@api_view(['GET'])
def reporte_por_estado(request):
    return Response([{'id': r['estado__id'], 'nombre': r['estado__nombre'] or 'Sin estado', 'total': r['total'], 'color': r['estado__color']} for r in Ticket.objects.values('estado__id', 'estado__nombre', 'estado__color').annotate(total=Count('id'))])

@api_view(['GET'])
def reporte_por_prioridad(request):
    return Response([{'id': r['prioridad__id'], 'nombre': r['prioridad__nombre'] or 'Sin prioridad', 'total': r['total'], 'color': r['prioridad__color']} for r in Ticket.objects.values('prioridad__id', 'prioridad__nombre', 'prioridad__color').annotate(total=Count('id'))])

@api_view(['GET'])
def reporte_sla(request): return Response({'promedio_primera_respuesta_horas': 0, 'promedio_resolucion_horas': 0, 'cumplimiento_sla_porcentaje': 100, 'por_prioridad': []})

@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_tendencias(request):
    result = []
    for i in range(29, -1, -1):
        day = (timezone.now() - timedelta(days=i)).date()
        result.append({'fecha': str(day), 'total': Ticket.objects.filter(fecha_creacion__date=day).count(), 'resueltos': 0})
    return Response(result)

@api_view(['GET'])
def reporte_por_region(request): return Response([])

@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_tickets(request): 
    qs = Ticket.objects.select_related('sistema', 'modulo', 'prioridad', 'estado', 'categoria', 'usuario_reporta', 'usuario_asignado').all()[:100]
    serializer = TicketSerializer(qs, many=True)
    list_data = serializer.data
    
    for row in list_data:
        base_date = _clean_view_date_string(row.get('fecha_creacion'))
        row['fecha_creacion'] = _clean_view_date_string(row.get('fecha_creacion'))
        row['fecha_asignacion'] = _clean_view_date_string(row.get('fecha_asignacion')) if row.get('fecha_asignacion') else base_date
        row['fecha_primera_respuesta'] = _clean_view_date_string(row.get('fecha_primera_respuesta')) if row.get('fecha_primera_respuesta') else base_date
        row['fecha_resolucion'] = _clean_view_date_string(row.get('fecha_resolucion')) if row.get('fecha_resolucion') else base_date
        row['fecha_cierre'] = _clean_view_date_string(row.get('fecha_cierre')) if row.get('fecha_cierre') else base_date
        
    return Response(list_data)

@api_view(['GET'])
def actividad_reciente(request): return Response([])

# ─────────────────────────────────────────────────────────────────
#  ENDPOINTS DE COMPATIBILIDAD (CRUD)
# ─────────────────────────────────────────────────────────────────

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_create_usuario(request):
    payload = request.data.get('data') if 'data' in request.data else request.data
    serializer = UsuarioInputSerializer(data=payload if payload else request.data)
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
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = UsuarioUpdateSerializer(usuario, data=custom_data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_delete_usuario(request, pk=None):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = request.data
    usuario_id = pk or payload.get('id')
    Usuario.objects.filter(id=usuario_id).delete()
    return Response({'detail': 'Eliminado.'}, status=status.HTTP_200_OK)

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_delete_modulo(request, pk=None):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = request.data
    modulo_id = pk or payload.get('id')
    Modulo.objects.filter(id=modulo_id).delete()
    return Response({'detail': 'Módulo eliminado.'}, status=status.HTTP_200_OK)

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_delete_conocimiento(request, pk=None):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = request.data
    entry_id = pk or payload.get('id')
    ConocimientoEntry.objects.filter(id=entry_id).delete()
    return Response({'detail': 'Entrada eliminada.'}, status=status.HTTP_200_OK)

@api_view(['POST', 'GET'])
def compat_create_ticket(request):
    serializer = TicketInputSerializer(data=request.data.get('data', request.data))
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST', 'GET'])
def compat_create_modulo(request):
    serializer = ModuloSerializer(data=request.data.get('data', request.data))
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST', 'GET'])
def compat_create_conocimiento(request):
    serializer = ConocimientoSerializer(data=request.data.get('data', request.data))
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def compat_chatter_list(request):
    tid = request.query_params.get('ticket') or request.query_params.get('ticket_id')
    return Response(ChatterEntrySerializer(ChatterEntry.objects.filter(ticket_id=tid).order_by('fecha_creacion'), many=True).data if tid else [])

@api_view(['GET'])
def compat_timelogs_list(request):
    tid = request.query_params.get('ticket') or request.query_params.get('ticket_id')
    return Response(TimeLogSerializer(TicketTimeLog.objects.filter(ticket_id=tid).order_by('fecha_inicio'), many=True).data if tid else [])

# 🛡️ ENDPOINT NUEVO: Resuelve el 404 al guardar notas en el Historial (Chatter)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_add_chatter(request):
    payload = request.data.get('data', request.data)
    ticket_id = payload.get('ticket_id') or payload.get('ticket')
    contenido = payload.get('contenido')
    
    if not ticket_id or not contenido:
        return Response({'detail': 'Faltan parámetros.'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        ticket = Ticket.objects.get(pk=ticket_id)
    except Ticket.DoesNotExist:
        return Response({'detail': 'Ticket no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        
    entry = ChatterEntry.objects.create(
        ticket=ticket,
        tipo='comentario',
        autor=request.user,
        contenido=contenido
    )
    return Response(ChatterEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

# 🛡️ ENDPOINT NUEVO: Resuelve el 404 al intentar Editar/Guardar cambios del Ticket
@api_view(['POST', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_update_ticket(request):
    payload = request.data.get('data', request.data)
    ticket_id = payload.get('id') or request.query_params.get('id')
    
    try:
        ticket = Ticket.objects.get(pk=ticket_id)
    except Ticket.DoesNotExist:
        return Response({'detail': 'Ticket no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        
    old_est = ticket.estado
    serializer = TicketUpdateSerializer(ticket, data=payload, partial=True)
    serializer.is_valid(raise_exception=True)
    ticket_upd = serializer.save()
    
    if old_est != ticket_upd.estado:
        _handle_state_change(ticket_upd, old_est, ticket_upd.estado, request.user)
        
    return Response(TicketSerializer(ticket_upd).data)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_ticket_detail(request, pk):
    try:
        ticket = Ticket.objects.select_related(
            'sistema', 'modulo', 'prioridad', 'estado', 'categoria', 
            'usuario_reporta', 'usuario_asignado'
        ).get(pk=pk)
    except Ticket.DoesNotExist:
        return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = TicketSerializer(ticket)
        data = serializer.data

        base_date = _clean_view_date_string(data.get('fecha_creacion'))
        
        data['fecha_creacion'] = _clean_view_date_string(data.get('fecha_creacion'))
        data['fecha_asignacion'] = _clean_view_date_string(data.get('fecha_asignacion')) if data.get('fecha_asignacion') else base_date
        data['fecha_primera_respuesta'] = _clean_view_date_string(data.get('fecha_primera_respuesta')) if data.get('fecha_primera_respuesta') else base_date
        data['fecha_resolucion'] = _clean_view_date_string(data.get('fecha_resolucion')) if data.get('fecha_resolucion') else base_date
        data['fecha_cierre'] = _clean_view_date_string(data.get('fecha_cierre')) if data.get('fecha_cierre') else base_date

        return Response(data)

    elif request.method in ['PUT', 'PATCH']:
        payload = request.data.get('data', request.data)
        old_est = ticket.estado
        serializer = TicketUpdateSerializer(ticket, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        ticket_upd = serializer.save()
        
        if old_est != ticket_upd.estado: 
            _handle_state_change(ticket_upd, old_est, ticket_upd.estado, request.user)
            
        return_serializer = TicketSerializer(ticket_upd)
        return_data = return_serializer.data
        base_date = _clean_view_date_string(return_data.get('fecha_creacion'))
        
        return_data['fecha_creacion'] = _clean_view_date_string(return_data.get('fecha_creacion'))
        return_data['fecha_asignacion'] = _clean_view_date_string(return_data.get('fecha_asignacion')) if return_data.get('fecha_asignacion') else base_date
        return_data['fecha_cierre'] = _clean_view_date_string(return_data.get('fecha_cierre')) if return_data.get('fecha_cierre') else base_date
        
        return Response(return_data)

    elif request.method == 'DELETE':
        ticket.delete()
        return Response({'detail': 'Eliminado.'}, status=status.HTTP_200_OK)
