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
# 🔴 IMPORTANTE: Añadir esta línea aquí arriba
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
    print("\n📬 DATA RECIBIDA DESDE EL FRONTEND:", request.data)
    
    # 🔴 CORRECCIÓN: Si el JSON viene envuelto en un objeto 'data', lo extraemos
    payload = request.data.get('data') if 'data' in request.data else request.data
    
    # Si por alguna razón payload es None, usamos un diccionario vacío para evitar caídas
    if payload is None:
        payload = {}

    correo = (
        payload.get('correo_electronico') or 
        payload.get('email') or 
        payload.get('username')
    )
    password = payload.get('password')
    
    if not correo or not password:
        return Response(
            {'detail': 'Faltan credenciales obligatorias (correo o password).'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    try:
        # Buscamos el usuario en Postgres
        user = Usuario.objects.get(correo_electronico=correo)
        
        # Validamos la contraseña
        if not user.check_password(password):
            return Response({'detail': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)
            
    except Usuario.DoesNotExist:
        return Response({'detail': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.activo:
        return Response({'detail': 'El usuario se encuentra inactivo.'}, status=status.HTTP_403_FORBIDDEN)

    # Recuperamos o creamos el token
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
@authentication_classes([TokenAuthentication]) # 🔴 ADICIÓN AQUÍ: Forzamos el uso de tu Token custom
@permission_classes([IsAuthenticated])
def me_view(request):
    serializer = UsuarioSerializer(request.user)
    return Response(serializer.data)


# ─────────────────────────────────────────────
#  HELPER — SLA PAUSE MANAGEMENT
# ─────────────────────────────────────────────

def _handle_state_change(ticket, old_estado, new_estado, user):
    """Manages SLA time logs when a ticket changes state."""
    now = timezone.now()

    # Close any open time logs if we're leaving a paused state
    if old_estado and old_estado.pausa_sla:
        open_log = TicketTimeLog.objects.filter(ticket=ticket, fecha_fin__isnull=True).first()
        if open_log:
            open_log.fecha_fin = now
            open_log.save()
            # Recalculate total pause minutes
            total_pause = TicketTimeLog.objects.filter(
                ticket=ticket, duracion_minutos__isnull=False
            ).aggregate(total=Count('duracion_minutos'))
            pause_minutes = sum(
                log.duracion_minutos for log in TicketTimeLog.objects.filter(ticket=ticket, duracion_minutos__isnull=False)
            )
            ticket.tiempo_pausa_minutos = pause_minutes
            ticket.save(update_fields=['tiempo_pausa_minutos'])

    # Open a new time log if entering a paused state
    if new_estado and new_estado.pausa_sla:
        TicketTimeLog.objects.create(
            ticket=ticket,
            estado_pausa=new_estado.nombre,
            fecha_inicio=now,
        )

    # Handle closure timestamps
    if new_estado and new_estado.es_estado_cierre:
        if not ticket.fecha_resolucion:
            ticket.fecha_resolucion = now
        ticket.fecha_cierre = now
        if ticket.fecha_creacion:
            delta = now - ticket.fecha_creacion
            ticket.tiempo_atencion_minutos = int(delta.total_seconds() / 60)
        ticket.save(update_fields=['fecha_resolucion', 'fecha_cierre', 'tiempo_atencion_minutos'])

    # Chatter entry for state change
    ChatterEntry.objects.create(
        ticket=ticket,
        tipo='cambio_estado',
        autor=user,
        estado_anterior=old_estado.nombre if old_estado else None,
        estado_nuevo=new_estado.nombre if new_estado else None,
        contenido=f"Estado cambiado de '{old_estado.nombre if old_estado else '—'}' a '{new_estado.nombre if new_estado else '—'}'",
    )


# ─────────────────────────────────────────────
#  TICKETS
# ─────────────────────────────────────────────

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.select_related(
        'sistema', 'modulo', 'prioridad', 'estado', 'categoria',
        'usuario_reporta', 'usuario_asignado'
    ).all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'prioridad', 'categoria', 'sistema', 'modulo', 'usuario_asignado', 'usuario_reporta']
    search_fields = ['folio', 'titulo', 'descripcion', 'codigo_error']
    ordering_fields = ['fecha_creacion', 'prioridad__orden', 'estado__orden']
    ordering = ['-fecha_creacion']

    # 🆕 AÑADIR ESTE MÉTODO PARA DESENVOLVER EL JSON DEL FRONTEND
    def create(self, request, *args, **kwargs):
        # Si el frontend envía los datos envueltos en {'data': {...}}, los extraemos
        data = request.data.get('data') if 'data' in request.data else request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    
    def get_queryset(self):
        qs = super().get_queryset()
        vista = self.request.query_params.get('vista')
        if not vista or vista == 'todos':
            return qs
        now = timezone.now()
        if vista == 'abiertos':
            return qs.filter(estado__es_estado_cierre=False)
        if vista == 'en_proceso':
            return qs.filter(estado__es_estado_cierre=False, usuario_asignado__isnull=False)
        if vista == 'resueltos':
            return qs.filter(estado__es_estado_cierre=True, fecha_cierre__isnull=True)
        if vista == 'cerrados':
            return qs.filter(estado__es_estado_cierre=True)
        if vista == 'hoy':
            return qs.filter(fecha_creacion__date=now.date())
        if vista == 'vencidos':
            vencidos_ids = []
            for t in qs.filter(estado__es_estado_cierre=False, prioridad__isnull=False).select_related('prioridad'):
                if t.prioridad and t.prioridad.sla_horas:
                    sla_limit = t.fecha_creacion + timedelta(hours=t.prioridad.sla_horas)
                    if now > sla_limit:
                        vencidos_ids.append(t.id)
            return qs.filter(id__in=vencidos_ids)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return TicketInputSerializer
        if self.action in ['partial_update', 'update']:
            return TicketUpdateSerializer
        return TicketSerializer

    def perform_create(self, serializer):
        ticket = serializer.save()
        estado = ticket.estado
        if estado and estado.pausa_sla:
            TicketTimeLog.objects.create(
                ticket=ticket,
                estado_pausa=estado.nombre,
                fecha_inicio=timezone.now(),
            )
        ChatterEntry.objects.create(
            ticket=ticket,
            tipo='sistema',
            autor=self.request.user if self.request.user.is_authenticated else None,
            contenido=f"Ticket creado con folio {ticket.folio}",
        )

    def perform_update(self, serializer):
        old = self.get_object()
        old_estado = old.estado
        ticket = serializer.save()
        new_estado = ticket.estado
        if old_estado != new_estado:
            _handle_state_change(ticket, old_estado, new_estado, self.request.user if self.request.user.is_authenticated else None)
        # Track first assignment
        if not old.usuario_asignado and ticket.usuario_asignado:
            ticket.fecha_asignacion = timezone.now()
            ticket.save(update_fields=['fecha_asignacion'])
            ChatterEntry.objects.create(
                ticket=ticket,
                tipo='asignacion',
                autor=self.request.user if self.request.user.is_authenticated else None,
                contenido=f"Ticket asignado a {ticket.usuario_asignado.nombre_completo}",
            )

    @action(detail=True, methods=['post'])
    def remind(self, request, pk=None):
        ticket = self.get_object()
        if not ticket.usuario_asignado:
            return Response({'message': 'El ticket no tiene usuario asignado.'}, status=status.HTTP_400_BAD_REQUEST)
        subject = f"[SEECH Tickets] Recordatorio: {ticket.folio} - {ticket.titulo}"
        message = (
            f"Hola {ticket.usuario_asignado.nombre_completo},\n\n"
            f"Este es un recordatorio sobre el ticket {ticket.folio}: \"{ticket.titulo}\".\n"
            f"Estado actual: {ticket.estado.nombre if ticket.estado else 'Sin estado'}\n"
            f"Prioridad: {ticket.prioridad.nombre if ticket.prioridad else 'Sin prioridad'}\n\n"
            f"Por favor atiende este ticket a la brevedad.\n\n"
            f"— Sistema de Tickets SEECH"
        )
        estado_nombre = ticket.estado.nombre if ticket.estado else 'Sin estado'
        prioridad_nombre = ticket.prioridad.nombre if ticket.prioridad else 'Sin prioridad'
        destinatario = ticket.usuario_asignado.correo_electronico
        try:
            resend_email.send_email(
                to=destinatario,
                subject=subject,
                text=message,
            )
        except resend_email.ResendError as exc:
            req_log = getattr(request, 'log', None)
            if req_log:
                req_log.error("Error enviando recordatorio con Resend: %s", exc)
            ChatterEntry.objects.create(
                ticket=ticket,
                tipo='sistema',
                autor=request.user if request.user.is_authenticated else None,
                contenido=(
                    f"No se pudo enviar el recordatorio a {ticket.usuario_asignado.nombre_completo} "
                    f"({destinatario}). El servicio de correo no está disponible."
                ),
            )
            return Response(
                {'message': 'No se pudo enviar el recordatorio. Intenta de nuevo más tarde.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        ChatterEntry.objects.create(
            ticket=ticket,
            tipo='sistema',
            autor=request.user if request.user.is_authenticated else None,
            contenido=(
                f"Recordatorio enviado a {ticket.usuario_asignado.nombre_completo} "
                f"({destinatario}). "
                f"Estado: {estado_nombre}. Prioridad: {prioridad_nombre}."
            ),
        )
        return Response({'message': f'Recordatorio enviado a {destinatario}'})

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        ticket = self.get_object()
        estado_anterior = ticket.estado
        # Reopen to an active state: "En Proceso" if assigned, otherwise "Nuevo"
        nombre_destino = 'En Proceso' if ticket.usuario_asignado_id else 'Nuevo'
        nuevo_estado = Estado.objects.filter(nombre=nombre_destino).first() or Estado.objects.filter(nombre='Nuevo').first()
        ticket.ticket_reabierto = True
        ticket.veces_reabierto += 1
        ticket.fecha_cierre = None
        ticket.fecha_resolucion = None
        if nuevo_estado:
            ticket.estado = nuevo_estado
        ticket.save(update_fields=['ticket_reabierto', 'veces_reabierto', 'fecha_cierre', 'fecha_resolucion', 'estado'])
        ChatterEntry.objects.create(
            ticket=ticket,
            tipo='sistema',
            autor=request.user if request.user.is_authenticated else None,
            contenido=f"Ticket reabierto (vez #{ticket.veces_reabierto})",
            estado_anterior=estado_anterior.nombre if estado_anterior else None,
            estado_nuevo=nuevo_estado.nombre if nuevo_estado else None,
        )
        serializer = TicketSerializer(ticket)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def chatter(self, request, pk=None):
        ticket = self.get_object()
        if request.method == 'GET':
            entries = ticket.chatter.select_related('autor').all()
            return Response(ChatterEntrySerializer(entries, many=True).data)
        serializer = ChatterInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = ChatterEntry.objects.create(
            ticket=ticket,
            tipo='comentario',
            autor=request.user if request.user.is_authenticated else None,
            contenido=serializer.validated_data['contenido'],
        )
        # Mark first response if not set
        if not ticket.fecha_primera_respuesta:
            ticket.fecha_primera_respuesta = timezone.now()
            ticket.save(update_fields=['fecha_primera_respuesta'])
        return Response(ChatterEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='time-logs')
    def time_logs(self, request, pk=None):
        ticket = self.get_object()
        logs = ticket.time_logs.all()
        return Response(TimeLogSerializer(logs, many=True).data)


# ─────────────────────────────────────────────
#  SISTEMAS
# ─────────────────────────────────────────────

class SistemaViewSet(viewsets.ModelViewSet):
    queryset = Sistema.objects.prefetch_related('modulos', 'tickets').all()
    serializer_class = SistemaSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'proveedor']
    pagination_class = None


# ─────────────────────────────────────────────
#  MODULOS
# ─────────────────────────────────────────────

class ModuloViewSet(viewsets.ModelViewSet):
    queryset = Modulo.objects.select_related('sistema').prefetch_related('tickets').all()
    serializer_class = ModuloSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['sistema']
    search_fields = ['nombre']
    pagination_class = None


# ─────────────────────────────────────────────
#  DOCUMENTOS
# ─────────────────────────────────────────────

class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = Documento.objects.select_related('sistema', 'modulo').all()
    serializer_class = DocumentoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sistema', 'modulo']
    pagination_class = None

    def perform_create(self, serializer):
        serializer.save(subido_por=self.request.user if self.request.user.is_authenticated else None)


# ─────────────────────────────────────────────
#  USUARIOS
# ─────────────────────────────────────────────

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['nivel_educativo', 'region_zona', 'rol']
    search_fields = ['nombre_completo', 'correo_electronico', 'numero_empleado', 'cct']
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioInputSerializer
        if self.action in ['partial_update', 'update']:
            return UsuarioUpdateSerializer
        return UsuarioSerializer


# ─────────────────────────────────────────────
#  CATALOGOS
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
#  CONOCIMIENTO
# ─────────────────────────────────────────────

class ConocimientoViewSet(viewsets.ModelViewSet):
    queryset = ConocimientoEntry.objects.select_related('sistema', 'modulo').all()
    serializer_class = ConocimientoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['sistema', 'causa_raiz']
    search_fields = ['titulo', 'codigo_error', 'descripcion_problema', 'solucion_aplicada']
    pagination_class = None

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.veces_consultado += 1
        instance.save(update_fields=['veces_consultado'])
        return Response(ConocimientoSerializer(instance).data)


# ─────────────────────────────────────────────
#  REPORTES
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_resumen(request):
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)

    total = Ticket.objects.count()
    abiertos = Ticket.objects.filter(estado__es_estado_cierre=False).count()
    resueltos = Ticket.objects.filter(estado__es_estado_cierre=True, fecha_cierre__isnull=True).count()
    cerrados = Ticket.objects.filter(estado__es_estado_cierre=True).count()
    en_proceso = Ticket.objects.filter(
        estado__es_estado_cierre=False,
        usuario_asignado__isnull=False
    ).count()

    # Vencidos: open tickets past their SLA
    vencidos = 0
    for ticket in Ticket.objects.filter(estado__es_estado_cierre=False, prioridad__isnull=False).select_related('prioridad', 'estado'):
        if ticket.prioridad and ticket.prioridad.sla_horas:
            sla_limit = ticket.fecha_creacion + timedelta(hours=ticket.prioridad.sla_horas)
            if now > sla_limit:
                vencidos += 1

    tickets_hoy = Ticket.objects.filter(fecha_creacion__date=today).count()
    tickets_semana = Ticket.objects.filter(fecha_creacion__gte=week_ago).count()

    avg_resolucion = Ticket.objects.filter(
        tiempo_atencion_minutos__isnull=False
    ).aggregate(avg=Avg('tiempo_atencion_minutos'))['avg'] or 0

    avg_calificacion = Ticket.objects.filter(
        calificacion_estrellas__isnull=False
    ).aggregate(avg=Avg('calificacion_estrellas'))['avg']

    # SLA compliance
    closed_tickets = Ticket.objects.filter(
        estado__es_estado_cierre=True,
        tiempo_atencion_minutos__isnull=False
    ).select_related('prioridad')
    sla_total = closed_tickets.count()
    sla_cumplido = 0
    for t in closed_tickets:
        if t.prioridad and t.prioridad.sla_horas:
            if (t.tiempo_atencion_minutos or 0) <= t.prioridad.sla_horas * 60:
                sla_cumplido += 1
    porcentaje_sla = (sla_cumplido / sla_total * 100) if sla_total > 0 else 100.0

    return Response({
        'total_tickets': total,
        'abiertos': abiertos,
        'en_proceso': en_proceso,
        'resueltos': resueltos,
        'cerrados': cerrados,
        'vencidos': vencidos,
        'tickets_hoy': tickets_hoy,
        'tickets_semana': tickets_semana,
        'promedio_resolucion_horas': round(avg_resolucion / 60, 2),
        'satisfaccion_promedio': round(avg_calificacion, 2) if avg_calificacion else None,
        'porcentaje_sla_cumplido': round(porcentaje_sla, 1),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_por_sistema(request):
    data = (
        Ticket.objects.values('sistema__id', 'sistema__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    return Response([
        {'id': row['sistema__id'], 'nombre': row['sistema__nombre'] or 'Sin sistema', 'total': row['total'], 'color': None}
        for row in data
    ])


@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_por_estado(request):
    data = (
        Ticket.objects.values('estado__id', 'estado__nombre', 'estado__color')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    return Response([
        {'id': row['estado__id'], 'nombre': row['estado__nombre'] or 'Sin estado', 'total': row['total'], 'color': row['estado__color']}
        for row in data
    ])


@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_por_prioridad(request):
    data = (
        Ticket.objects.values('prioridad__id', 'prioridad__nombre', 'prioridad__color')
        .annotate(total=Count('id'))
        .order_by('prioridad__orden')
    )
    return Response([
        {'id': row['prioridad__id'], 'nombre': row['prioridad__nombre'] or 'Sin prioridad', 'total': row['total'], 'color': row['prioridad__color']}
        for row in data
    ])


@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_sla(request):
    closed = Ticket.objects.filter(estado__es_estado_cierre=True, tiempo_atencion_minutos__isnull=False)
    avg_resolucion = closed.aggregate(avg=Avg('tiempo_atencion_minutos'))['avg'] or 0
    avg_respuesta = Ticket.objects.filter(
        fecha_primera_respuesta__isnull=False
    ).annotate().aggregate(avg=Avg('tiempo_atencion_minutos'))['avg'] or 0

    total = closed.count()
    sla_cumplido = sum(
        1 for t in closed.select_related('prioridad')
        if t.prioridad and t.prioridad.sla_horas and (t.tiempo_atencion_minutos or 0) <= t.prioridad.sla_horas * 60
    )
    porcentaje = (sla_cumplido / total * 100) if total > 0 else 100.0

    # By priority
    por_prioridad = []
    for p in Prioridad.objects.all():
        tickets_p = closed.filter(prioridad=p)
        if not tickets_p.exists():
            continue
        avg_p = tickets_p.aggregate(avg=Avg('tiempo_atencion_minutos'))['avg'] or 0
        total_p = tickets_p.count()
        cumplidos_p = sum(1 for t in tickets_p if (t.tiempo_atencion_minutos or 0) <= p.sla_horas * 60)
        por_prioridad.append({
            'prioridad': p.nombre,
            'promedio_horas': round(avg_p / 60, 2),
            'cumplimiento_porcentaje': round(cumplidos_p / total_p * 100, 1) if total_p > 0 else 100.0,
        })

    return Response({
        'promedio_primera_respuesta_horas': round(avg_respuesta / 60, 2),
        'promedio_resolucion_horas': round(avg_resolucion / 60, 2),
        'cumplimiento_sla_porcentaje': round(porcentaje, 1),
        'por_prioridad': por_prioridad,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_tendencias(request):
    periodo = request.query_params.get('periodo', 'mes')
    now = timezone.now()
    if periodo == 'semana':
        days = 7
    elif periodo == 'trimestre':
        days = 90
    else:
        days = 30

    result = []
    for i in range(days - 1, -1, -1):
        day = (now - timedelta(days=i)).date()
        total = Ticket.objects.filter(fecha_creacion__date=day).count()
        resueltos = Ticket.objects.filter(fecha_creacion__date=day, estado__es_estado_cierre=True).count()
        result.append({'fecha': str(day), 'total': total, 'resueltos': resueltos})
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_por_region(request):
    data = (
        Ticket.objects.filter(usuario_reporta__isnull=False)
        .values('usuario_reporta__region_zona')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    return Response([
        {'id': None, 'nombre': row['usuario_reporta__region_zona'] or 'Sin región', 'total': row['total'], 'color': None}
        for row in data
    ])


@api_view(['GET'])
@permission_classes([AllowAny])
def reporte_tickets(request):
    qs = Ticket.objects.select_related(
        'sistema', 'modulo', 'prioridad', 'estado', 'categoria',
        'usuario_reporta', 'usuario_asignado'
    ).all()

    p = request.query_params

    def _int(name):
        v = p.get(name)
        if v not in (None, '', 'todos'):
            try:
                return int(v)
            except (TypeError, ValueError):
                return None
        return None

    def _str(name):
        v = p.get(name)
        if v not in (None, '', 'todos'):
            return v
        return None

    fk_filters = {
        'usuario_asignado_id': _int('usuario_asignado'),
        'estado_id': _int('estado'),
        'prioridad_id': _int('prioridad'),
        'categoria_id': _int('categoria'),
        'sistema_id': _int('sistema'),
        'modulo_id': _int('modulo'),
    }
    for field, value in fk_filters.items():
        if value is not None:
            qs = qs.filter(**{field: value})

    impacto = _str('impacto')
    if impacto is not None:
        qs = qs.filter(impacto_proceso=impacto)

    str_filters = {
        'usuario_reporta__region_zona': _str('region'),
        'usuario_reporta__puesto_cargo': _str('puesto'),
        'usuario_reporta__cct': _str('cct'),
        'usuario_reporta__nivel_educativo': _str('nivel_educativo'),
    }
    for field, value in str_filters.items():
        if value is not None:
            qs = qs.filter(**{field: value})

    qs = qs.order_by('-fecha_creacion')[:1000]
    return Response(TicketSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def actividad_reciente(request):
    entries = ChatterEntry.objects.select_related('autor', 'ticket').order_by('-fecha_creacion')[:20]
    return Response([
        {
            'id': e.id,
            'tipo': e.tipo,
            'descripcion': e.contenido or '',
            'ticket_id': e.ticket_id,
            'ticket_folio': e.ticket.folio if e.ticket else None,
            'usuario_nombre': e.autor.nombre_completo if e.autor else None,
            'fecha': e.fecha_creacion.isoformat(),
        }
        for e in entries
    ])

# ─────────────────────────────────────────────────────────────────
#  NUEVAS VISTAS PLANAS DE COMPATIBILIDAD (EVITAN ENRUTAMIENTOS RAROS)
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
    
    usuario_id = pk or payload.get('id')
    if not usuario_id:
        return Response({'detail': 'Falta el ID del usuario.'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        
    serializer = UsuarioUpdateSerializer(usuario, data=payload, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_create_ticket(request):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = request.data
    
    serializer = TicketInputSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_create_modulo(request):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = request.data
    
    serializer = ModuloSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_create_conocimiento(request):
    payload = request.data.get('data') if 'data' in request.data else request.data
    if payload is None: payload = request.data
    
    # 🔴 CORRECCIÓN: Nombre exacto del serializador sincronizado
    serializer = ConocimientoSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────
# 🆕 COMPATIBILIDAD DE SUB-RECURSOS DEL DETALLE DE TICKET
# ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_chatter_list(request):
    """Devuelve las entradas de chatter filtradas por el ticket solicitado por el frontend."""
    ticket_id = request.query_params.get('ticket') or request.query_params.get('ticket_id')
    if ticket_id:
        entries = ChatterEntry.objects.filter(ticket_id=ticket_id).select_related('autor').order_by('fecha_creacion')
        return Response(ChatterEntrySerializer(entries, many=True).data)
    return Response([]) # Retorna lista vacía segura para evitar errores de .split()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def compat_timelogs_list(request):
    """Devuelve los registros de tiempo filtrados por el ticket solicitado."""
    ticket_id = request.query_params.get('ticket') or request.query_params.get('ticket_id')
    if ticket_id:
        logs = TicketTimeLog.objects.filter(ticket_id=ticket_id).order_by('fecha_inicio')
        return Response(TimeLogSerializer(logs, many=True).data)
    return Response([])
