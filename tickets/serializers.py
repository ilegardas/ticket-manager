from rest_framework import serializers
from .models import (
    Usuario, Sistema, Modulo, Documento, Prioridad, Estado, Categoria,
    Ticket, ChatterEntry, TicketTimeLog, ConocimientoEntry
)

# ─────────────────────────────────────────────────────────────────
#  USUARIOS
# ─────────────────────────────────────────────────────────────────

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            'id', 'correo_electronico', 'nombre_completo', 'numero_empleado',
            'puesto_cargo', 'cct', 'region_zona', 'nivel_educativo', 'rol',
            'activo', 'fecha_registro',
        ]
        read_only_fields = ['id', 'fecha_registro']


class UsuarioInputSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = Usuario
        fields = [
            'correo_electronico', 'nombre_completo', 'password',
            'numero_empleado', 'puesto_cargo', 'cct', 'region_zona',
            'nivel_educativo', 'rol',
        ]
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    activo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    id = serializers.IntegerField(read_only=True, required=False)
    correo_electronico = serializers.EmailField(read_only=True, required=False)
    class Meta:
        model = Usuario
        fields = [
            'id', 'correo_electronico', 'nombre_completo', 'numero_empleado', 
            'puesto_cargo', 'cct', 'region_zona', 'nivel_educativo', 'rol', 'activo',
        ]
        read_only_fields = ['id', 'correo_electronico']
    def validate_activo(self, value):
        if value in ['Activo', 'activo', 'true', 'True', True, 1, '1']: return True
        if value in ['Inactivo', 'inactivo', 'false', 'False', False, 0, '0']: return False
        if self.instance: return self.instance.activo
        return True

# ─────────────────────────────────────────────────────────────────
#  SISTEMAS Y MÓDULOS
# ─────────────────────────────────────────────────────────────────

class SistemaSerializer(serializers.ModelSerializer):
    total_tickets = serializers.SerializerMethodField()
    total_modulos = serializers.SerializerMethodField()
    class Meta:
        model = Sistema
        fields = ['id', 'nombre', 'descripcion', 'version', 'proveedor', 'activo', 'total_tickets', 'total_modulos', 'fecha_creacion']
    def get_total_tickets(self, obj): return obj.tickets.count() if hasattr(obj, 'tickets') else 0
    def get_total_modulos(self, obj): return obj.modulos.count() if hasattr(obj, 'modulos') else 0


class ModuloSerializer(serializers.ModelSerializer):
    sistema_id = serializers.PrimaryKeyRelatedField(source='sistema', queryset=Sistema.objects.all())
    sistema_nombre = serializers.CharField(source='sistema.nombre', read_only=True, default="")
    total_tickets = serializers.SerializerMethodField()
    class Meta:
        model = Modulo
        fields = ['id', 'nombre', 'descripcion', 'sistema_id', 'sistema_nombre', 'activo', 'total_tickets', 'fecha_creacion']
    def get_total_tickets(self, obj): return obj.tickets.count() if hasattr(obj, 'tickets') else 0

# ─────────────────────────────────────────────────────────────────
#  DOCUMENTOS Y CATÁLOGOS
# ─────────────────────────────────────────────────────────────────

class DocumentoSerializer(serializers.ModelSerializer):
    sistema_id = serializers.PrimaryKeyRelatedField(source='sistema', queryset=Sistema.objects.all(), allow_null=True, required=False)
    modulo_id = serializers.PrimaryKeyRelatedField(source='modulo', queryset=Modulo.objects.all(), allow_null=True, required=False)
    class Meta:
        model = Documento
        fields = ['id', 'nombre', 'descripcion', 'tipo_archivo', 'url', 'sistema_id', 'modulo_id', 'subido_por_id', 'fecha_subida']


class PrioridadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prioridad
        fields = ['id', 'nombre', 'sla_horas', 'color', 'orden']


class EstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estado
        fields = ['id', 'nombre', 'es_estado_cierre', 'pausa_sla', 'color', 'orden']


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion', 'color']

# ─────────────────────────────────────────────────────────────────
#  TICKETS (🛡️ REMOCIÓN DE ZONA HORARIA LOCAL EN FECHAS)
# ─────────────────────────────────────────────────────────────────

class TicketSerializer(serializers.ModelSerializer):
    sistema_nombre = serializers.CharField(source='sistema.nombre', read_only=True, default="")
    modulo_nombre = serializers.CharField(source='modulo.nombre', read_only=True, default="")
    prioridad_nombre = serializers.CharField(source='prioridad.nombre', read_only=True, default="")
    prioridad_color = serializers.CharField(source='prioridad.color', read_only=True, default="")
    estado_nombre = serializers.CharField(source='estado.nombre', read_only=True, default="")
    estado_color = serializers.CharField(source='estado.color', read_only=True, default="")
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True, default="")
    usuario_reporta_nombre = serializers.CharField(source='usuario_reporta.nombre_completo', read_only=True, default="")
    usuario_asignado_nombre = serializers.CharField(source='usuario_asignado.nombre_completo', read_only=True, default="")
    tiempo_efectivo_minutos = serializers.ReadOnlyField()

    sistema_id = serializers.PrimaryKeyRelatedField(source='sistema', queryset=Sistema.objects.all(), allow_null=True, required=False)
    modulo_id = serializers.PrimaryKeyRelatedField(source='modulo', queryset=Modulo.objects.all(), allow_null=True, required=False)
    prioridad_id = serializers.PrimaryKeyRelatedField(source='prioridad', queryset=Prioridad.objects.all(), allow_null=True, required=False)
    estado_id = serializers.PrimaryKeyRelatedField(source='estado', queryset=Estado.objects.all(), allow_null=True, required=False)
    categoria_id = serializers.PrimaryKeyRelatedField(source='categoria', queryset=Categoria.objects.all(), allow_null=True, required=False)
    usuario_reporta_id = serializers.PrimaryKeyRelatedField(source='usuario_reporta', queryset=Usuario.objects.all(), allow_null=True, required=False)
    usuario_asignado_id = serializers.PrimaryKeyRelatedField(source='usuario_asignado', queryset=Usuario.objects.all(), allow_null=True, required=False)

    fecha_creacion = serializers.SerializerMethodField()
    fecha_asignacion = serializers.SerializerMethodField()
    fecha_primera_respuesta = serializers.SerializerMethodField()
    fecha_resolucion = serializers.SerializerMethodField()
    fecha_cierre = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'folio', 'titulo', 'descripcion', 'impacto_proceso', 'medio_ingreso',
            'sistema_id', 'sistema_nombre', 'modulo_id', 'modulo_nombre',
            'prioridad_id', 'prioridad_nombre', 'prioridad_color',
            'estado_id', 'estado_nombre', 'estado_color',
            'categoria_id', 'categoria_nombre',
            'usuario_reporta_id', 'usuario_reporta_nombre',
            'usuario_asignado_id', 'usuario_asignado_nombre',
            'fecha_creacion', 'fecha_asignacion', 'fecha_primera_respuesta',
            'fecha_resolucion', 'fecha_cierre',
            'tiempo_atencion_minutos', 'tiempo_efectivo_minutos', 'tiempo_pausa_minutos',
            'codigo_error', 'solucion_aplicada', 'causa_raiz',
            'calificacion_estrellas', 'ticket_reabierto', 'veces_reabierto',
        ]

    def _format_clean_iso(self, dt_value):
        if not dt_value:
            return "2026-06-24T00:00:00Z"
        # Forzamos formato estricto UTC con la 'Z' al final libre de desfases locales (-06:00)
        return dt_value.strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_fecha_creacion(self, obj):
        return self._format_clean_iso(obj.fecha_creacion)

    def get_fecha_asignacion(self, obj):
        return self._format_clean_iso(obj.fecha_asignacion) if obj.fecha_asignacion else self.get_fecha_creacion(obj)

    def get_fecha_primera_respuesta(self, obj):
        return self._format_clean_iso(obj.fecha_primera_respuesta) if obj.fecha_primera_respuesta else self.get_fecha_creacion(obj)

    def get_fecha_resolucion(self, obj):
        return self._format_clean_iso(obj.fecha_resolucion) if obj.fecha_resolucion else self.get_fecha_creacion(obj)

    def get_fecha_cierre(self, obj):
        return self._format_clean_iso(obj.fecha_cierre) if obj.fecha_cierre else self.get_fecha_creacion(obj)


class TicketInputSerializer(serializers.ModelSerializer):
    sistema_id = serializers.PrimaryKeyRelatedField(source='sistema', queryset=Sistema.objects.all(), allow_null=True, required=False)
    modulo_id = serializers.PrimaryKeyRelatedField(source='modulo', queryset=Modulo.objects.all(), allow_null=True, required=False)
    prioridad_id = serializers.PrimaryKeyRelatedField(source='prioridad', queryset=Prioridad.objects.all(), allow_null=True, required=False)
    estado_id = serializers.PrimaryKeyRelatedField(source='estado', queryset=Estado.objects.all(), allow_null=True, required=False)
    categoria_id = serializers.PrimaryKeyRelatedField(source='categoria', queryset=Categoria.objects.all(), allow_null=True, required=False)
    usuario_reporta_id = serializers.PrimaryKeyRelatedField(source='usuario_reporta', queryset=Usuario.objects.all(), allow_null=True, required=False)
    usuario_asignado_id = serializers.PrimaryKeyRelatedField(source='usuario_asignado', queryset=Usuario.objects.all(), allow_null=True, required=False)
    class Meta:
        model = Ticket
        fields = ['titulo', 'descripcion', 'impacto_proceso', 'medio_ingreso', 'sistema_id', 'modulo_id', 'prioridad_id', 'estado_id', 'categoria_id', 'usuario_reporta_id', 'usuario_asignado_id']


class TicketUpdateSerializer(serializers.ModelSerializer):
    sistema_id = serializers.PrimaryKeyRelatedField(source='sistema', queryset=Sistema.objects.all(), allow_null=True, required=False)
    modulo_id = serializers.PrimaryKeyRelatedField(source='modulo', queryset=Modulo.objects.all(), allow_null=True, required=False)
    # ✅ CORREGIDO: Se removió la referencia rota a Independent.objects y se asignó Estado de forma limpia
    estado_id = serializers.PrimaryKeyRelatedField(source='estado', queryset=Estado.objects.all(), allow_null=True, required=False)
    categoria_id = serializers.PrimaryKeyRelatedField(source='categoria', queryset=Categoria.objects.all(), allow_null=True, required=False)
    usuario_asignado_id = serializers.PrimaryKeyRelatedField(source='usuario_asignado', queryset=Usuario.objects.all(), allow_null=True, required=False)
    class Meta:
        model = Ticket
        fields = ['titulo', 'descripcion', 'impacto_proceso', 'medio_ingreso', 'sistema_id', 'modulo_id', 'prioridad_id', 'estado_id', 'categoria_id', 'usuario_asignado_id', 'codigo_error', 'solucion_aplicada', 'causa_raiz', 'calificacion_estrellas']

# ─────────────────────────────────────────────────────────────────
#  CHATTER, LOGS Y CONOCIMIENTO
# ─────────────────────────────────────────────────────────────────

class ChatterEntrySerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source='autor.nombre_completo', read_only=True, default="")
    fecha_creacion = serializers.SerializerMethodField()
    class Meta:
        model = ChatterEntry
        fields = ['id', 'ticket_id', 'tipo', 'contenido', 'autor_id', 'autor_nombre', 'estado_anterior', 'estado_nuevo', 'fecha_creacion']
    def get_fecha_creacion(self, obj): return obj.fecha_creacion.isoformat() if obj.fecha_creacion else "1970-01-01T00:00:00Z"


class ChatterInputSerializer(serializers.Serializer):
    contenido = serializers.CharField()


class TimeLogSerializer(serializers.ModelSerializer):
    fecha_inicio = serializers.SerializerMethodField()
    fecha_fin = serializers.SerializerMethodField()
    class Meta:
        model = TicketTimeLog
        fields = ['id', 'ticket_id', 'estado_pausa', 'fecha_inicio', 'fecha_fin', 'duracion_minutos']
    def get_fecha_inicio(self, obj): return obj.fecha_inicio.isoformat() if obj.fecha_inicio else "1970-01-01T00:00:00Z"
    def get_fecha_fin(self, obj): return obj.fecha_fin.isoformat() if obj.fecha_fin else obj.fecha_inicio.isoformat()


class ConocimientoSerializer(serializers.ModelSerializer):
    sistema_nombre = serializers.CharField(source='sistema.nombre', read_only=True, default="")
    fecha_creacion = serializers.SerializerMethodField()
    class Meta:
        model = ConocimientoEntry
        fields = ['id', 'titulo', 'descripcion_problema', 'codigo_error', 'solucion_aplicada', 'causa_raiz', 'sistema_id', 'sistema_nombre', 'modulo_id', 'ticket_origen_id', 'veces_consultado', 'fecha_creacion']
    def get_fecha_creacion(self, obj): return obj.fecha_creacion.isoformat() if obj.fecha_creacion else "1970-01-01T00:00:00Z"
