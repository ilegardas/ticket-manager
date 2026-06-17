from rest_framework import serializers
from .models import (
    Usuario, Sistema, Modulo, Documento, Prioridad, Estado, Categoria,
    Ticket, ChatterEntry, TicketTimeLog, ConocimientoEntry
)


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
    class Meta:
        model = Usuario
        fields = [
            'nombre_completo', 'numero_empleado', 'puesto_cargo', 'cct',
            'region_zona', 'nivel_educativo', 'rol', 'activo',
        ]


class SistemaSerializer(serializers.ModelSerializer):
    total_tickets = serializers.SerializerMethodField()
    total_modulos = serializers.SerializerMethodField()

    class Meta:
        model = Sistema
        fields = [
            'id', 'nombre', 'descripcion', 'version', 'proveedor',
            'activo', 'total_tickets', 'total_modulos', 'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion']

    def get_total_tickets(self, obj):
        return obj.tickets.count()

    def get_total_modulos(self, obj):
        return obj.modulos.count()


class ModuloSerializer(serializers.ModelSerializer):
    sistema_id = serializers.PrimaryKeyRelatedField(
        source='sistema', queryset=Sistema.objects.all())
    sistema_nombre = serializers.CharField(source='sistema.nombre', read_only=True)
    total_tickets = serializers.SerializerMethodField()

    class Meta:
        model = Modulo
        fields = [
            'id', 'nombre', 'descripcion', 'sistema_id', 'sistema_nombre',
            'activo', 'total_tickets', 'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'sistema_nombre']

    def get_total_tickets(self, obj):
        return obj.tickets.count()


class DocumentoSerializer(serializers.ModelSerializer):
    sistema_id = serializers.PrimaryKeyRelatedField(
        source='sistema', queryset=Sistema.objects.all(), allow_null=True, required=False,
    )
    modulo_id = serializers.PrimaryKeyRelatedField(
        source='modulo', queryset=Modulo.objects.all(), allow_null=True, required=False,
    )

    class Meta:
        model = Documento
        fields = [
            'id', 'nombre', 'descripcion', 'tipo_archivo', 'url',
            'sistema_id', 'modulo_id', 'subido_por_id', 'fecha_subida',
        ]
        read_only_fields = ['id', 'fecha_subida', 'subido_por_id']


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


class TicketSerializer(serializers.ModelSerializer):
    sistema_nombre = serializers.CharField(source='sistema.nombre', read_only=True, allow_null=True)
    modulo_nombre = serializers.CharField(source='modulo.nombre', read_only=True, allow_null=True)
    prioridad_nombre = serializers.CharField(source='prioridad.nombre', read_only=True, allow_null=True)
    prioridad_color = serializers.CharField(source='prioridad.color', read_only=True, allow_null=True)
    estado_nombre = serializers.CharField(source='estado.nombre', read_only=True, allow_null=True)
    estado_color = serializers.CharField(source='estado.color', read_only=True, allow_null=True)
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True, allow_null=True)
    usuario_reporta_nombre = serializers.CharField(source='usuario_reporta.nombre_completo', read_only=True, allow_null=True)
    usuario_asignado_nombre = serializers.CharField(source='usuario_asignado.nombre_completo', read_only=True, allow_null=True)
    tiempo_efectivo_minutos = serializers.ReadOnlyField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'folio', 'titulo', 'descripcion', 'impacto_proceso', 'medio_ingreso',
            'sistema_id', 'sistema_nombre',
            'modulo_id', 'modulo_nombre',
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
        read_only_fields = ['id', 'folio', 'fecha_creacion']


class TicketInputSerializer(serializers.ModelSerializer):
    sistema_id = serializers.PrimaryKeyRelatedField(
        source='sistema', queryset=Sistema.objects.all(), allow_null=True, required=False)
    modulo_id = serializers.PrimaryKeyRelatedField(
        source='modulo', queryset=Modulo.objects.all(), allow_null=True, required=False)
    prioridad_id = serializers.PrimaryKeyRelatedField(
        source='prioridad', queryset=Prioridad.objects.all(), allow_null=True, required=False)
    estado_id = serializers.PrimaryKeyRelatedField(
        source='estado', queryset=Estado.objects.all(), allow_null=True, required=False)
    categoria_id = serializers.PrimaryKeyRelatedField(
        source='categoria', queryset=Categoria.objects.all(), allow_null=True, required=False)
    usuario_reporta_id = serializers.PrimaryKeyRelatedField(
        source='usuario_reporta', queryset=Usuario.objects.all(), allow_null=True, required=False)
    usuario_asignado_id = serializers.PrimaryKeyRelatedField(
        source='usuario_asignado', queryset=Usuario.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Ticket
        fields = [
            'titulo', 'descripcion', 'impacto_proceso', 'medio_ingreso',
            'sistema_id', 'modulo_id', 'prioridad_id', 'estado_id', 'categoria_id',
            'usuario_reporta_id', 'usuario_asignado_id',
        ]


class TicketUpdateSerializer(serializers.ModelSerializer):
    sistema_id = serializers.PrimaryKeyRelatedField(
        source='sistema', queryset=Sistema.objects.all(), allow_null=True, required=False)
    modulo_id = serializers.PrimaryKeyRelatedField(
        source='modulo', queryset=Modulo.objects.all(), allow_null=True, required=False)
    prioridad_id = serializers.PrimaryKeyRelatedField(
        source='prioridad', queryset=Prioridad.objects.all(), allow_null=True, required=False)
    estado_id = serializers.PrimaryKeyRelatedField(
        source='estado', queryset=Estado.objects.all(), allow_null=True, required=False)
    categoria_id = serializers.PrimaryKeyRelatedField(
        source='categoria', queryset=Categoria.objects.all(), allow_null=True, required=False)
    usuario_asignado_id = serializers.PrimaryKeyRelatedField(
        source='usuario_asignado', queryset=Usuario.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Ticket
        fields = [
            'titulo', 'descripcion', 'impacto_proceso', 'medio_ingreso',
            'sistema_id', 'modulo_id', 'prioridad_id', 'estado_id', 'categoria_id',
            'usuario_asignado_id', 'codigo_error', 'solucion_aplicada', 'causa_raiz',
            'calificacion_estrellas',
        ]


class ChatterEntrySerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source='autor.nombre_completo', read_only=True, allow_null=True)

    class Meta:
        model = ChatterEntry
        fields = [
            'id', 'ticket_id', 'tipo', 'contenido', 'autor_id', 'autor_nombre',
            'estado_anterior', 'estado_nuevo', 'fecha_creacion',
        ]
        read_only_fields = ['id', 'ticket_id', 'tipo', 'autor_id', 'estado_anterior', 'estado_nuevo', 'fecha_creacion']


class ChatterInputSerializer(serializers.Serializer):
    contenido = serializers.CharField()


class TimeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketTimeLog
        fields = ['id', 'ticket_id', 'estado_pausa', 'fecha_inicio', 'fecha_fin', 'duracion_minutos']


class ConocimientoSerializer(serializers.ModelSerializer):
    sistema_nombre = serializers.CharField(source='sistema.nombre', read_only=True, allow_null=True)

    class Meta:
        model = ConocimientoEntry
        fields = [
            'id', 'titulo', 'descripcion_problema', 'codigo_error',
            'solucion_aplicada', 'causa_raiz',
            'sistema_id', 'sistema_nombre', 'modulo_id', 'ticket_origen_id',
            'veces_consultado', 'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'veces_consultado', 'sistema_nombre']
