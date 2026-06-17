from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import hashlib
import os


class UsuarioManager(BaseUserManager):
    def create_user(self, correo_electronico, nombre_completo, password=None, **extra_fields):
        if not correo_electronico:
            raise ValueError('El correo electrónico es requerido')
        correo_electronico = self.normalize_email(correo_electronico)
        user = self.model(correo_electronico=correo_electronico, nombre_completo=nombre_completo, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo_electronico, nombre_completo, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', 'admin')
        return self.create_user(correo_electronico, nombre_completo, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('tecnico', 'Técnico'),
        ('usuario', 'Usuario'),
    ]
    correo_electronico = models.EmailField(unique=True)
    nombre_completo = models.CharField(max_length=200)
    numero_empleado = models.CharField(max_length=50, blank=True, null=True)
    puesto_cargo = models.CharField(max_length=200, blank=True, null=True)
    cct = models.CharField(max_length=50, blank=True, null=True, verbose_name='CCT')
    region_zona = models.CharField(max_length=100, blank=True, null=True)
    nivel_educativo = models.CharField(max_length=100, blank=True, null=True)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='usuario')
    activo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo_electronico'
    REQUIRED_FIELDS = ['nombre_completo']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.nombre_completo

    @property
    def is_active(self):
        return self.activo

    @is_active.setter
    def is_active(self, value):
        self.activo = value


class Token(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='tokens')
    key = models.CharField(max_length=64, unique=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Token'

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = hashlib.sha256(os.urandom(32)).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Token de {self.usuario.nombre_completo}"


class Sistema(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=50, blank=True, null=True)
    proveedor = models.CharField(max_length=200, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sistema'
        verbose_name_plural = 'Sistemas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Modulo(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    sistema = models.ForeignKey(Sistema, on_delete=models.CASCADE, related_name='modulos')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Módulo'
        verbose_name_plural = 'Módulos'
        ordering = ['sistema__nombre', 'nombre']

    def __str__(self):
        return f"{self.sistema.nombre} / {self.nombre}"


class Documento(models.Model):
    nombre = models.CharField(max_length=300)
    descripcion = models.TextField(blank=True, null=True)
    tipo_archivo = models.CharField(max_length=50)
    url = models.URLField(max_length=1000)
    sistema = models.ForeignKey(Sistema, on_delete=models.CASCADE, related_name='documentos', null=True, blank=True)
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name='documentos', null=True, blank=True)
    subido_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['-fecha_subida']

    def __str__(self):
        return self.nombre


class Prioridad(models.Model):
    nombre = models.CharField(max_length=100)
    sla_horas = models.IntegerField(default=24)
    color = models.CharField(max_length=20, default='#6B7280')
    orden = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Prioridad'
        verbose_name_plural = 'Prioridades'
        ordering = ['orden']

    def __str__(self):
        return self.nombre


class Estado(models.Model):
    nombre = models.CharField(max_length=100)
    es_estado_cierre = models.BooleanField(default=False)
    pausa_sla = models.BooleanField(default=False, help_text='Si es True, el tiempo en este estado no cuenta para el SLA')
    color = models.CharField(max_length=20, default='#6B7280')
    orden = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'
        ordering = ['orden']

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=20, default='#6B7280')

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Ticket(models.Model):
    IMPACTO_CHOICES = [
        ('caido_total', 'Caído Total'),
        ('parcial', 'Parcialmente Funcional / Degradado'),
        ('funcional', 'Funcional'),
        ('mejora', 'Requerimiento de Mejora'),
    ]
    MEDIO_CHOICES = [
        ('portal', 'Portal Web'),
        ('correo', 'Correo'),
        ('telefono', 'Teléfono'),
        ('oficio', 'Oficio'),
    ]
    CAUSA_RAIZ_CHOICES = [
        ('bug_codigo', 'Bug de Código'),
        ('caida_servidor', 'Caída de Servidor'),
        ('error_humano', 'Error Humano'),
        ('datos_corruptos', 'Datos Corruptos'),
        ('configuracion', 'Error de Configuración'),
        ('red', 'Problema de Red'),
        ('permisos', 'Problema de Permisos'),
        ('otro', 'Otro'),
    ]

    folio = models.CharField(max_length=50, unique=True, blank=True)
    titulo = models.CharField(max_length=500)
    descripcion = models.TextField(blank=True, null=True)
    impacto_proceso = models.CharField(max_length=20, choices=IMPACTO_CHOICES, blank=True, null=True)
    medio_ingreso = models.CharField(max_length=20, choices=MEDIO_CHOICES, default='portal')

    sistema = models.ForeignKey(Sistema, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    modulo = models.ForeignKey(Modulo, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    prioridad = models.ForeignKey(Prioridad, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    estado = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')

    usuario_reporta = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_reportados')
    usuario_asignado = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_asignados')

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    fecha_primera_respuesta = models.DateTimeField(null=True, blank=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    tiempo_atencion_minutos = models.IntegerField(null=True, blank=True)
    tiempo_pausa_minutos = models.IntegerField(default=0)

    codigo_error = models.CharField(max_length=200, blank=True, null=True)
    solucion_aplicada = models.TextField(blank=True, null=True)
    causa_raiz = models.CharField(max_length=30, choices=CAUSA_RAIZ_CHOICES, blank=True, null=True)
    calificacion_estrellas = models.IntegerField(null=True, blank=True)

    ticket_reabierto = models.BooleanField(default=False)
    veces_reabierto = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.folio} - {self.titulo}"

    def save(self, *args, **kwargs):
        if not self.folio:
            year = timezone.now().year
            count = Ticket.objects.filter(fecha_creacion__year=year).count() + 1
            self.folio = f"TIC-{year}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def tiempo_efectivo_minutos(self):
        if self.tiempo_atencion_minutos is None:
            return None
        return max(0, self.tiempo_atencion_minutos - (self.tiempo_pausa_minutos or 0))


class ChatterEntry(models.Model):
    TIPO_CHOICES = [
        ('comentario', 'Comentario'),
        ('cambio_estado', 'Cambio de Estado'),
        ('asignacion', 'Asignación'),
        ('sistema', 'Mensaje del Sistema'),
    ]
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='chatter')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='comentario')
    contenido = models.TextField(blank=True, null=True)
    autor = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    estado_anterior = models.CharField(max_length=100, blank=True, null=True)
    estado_nuevo = models.CharField(max_length=100, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Entrada de Chatter'
        verbose_name_plural = 'Entradas de Chatter'
        ordering = ['fecha_creacion']

    def __str__(self):
        return f"{self.ticket.folio} - {self.tipo} ({self.fecha_creacion})"


class TicketTimeLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='time_logs')
    estado_pausa = models.CharField(max_length=100)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField(null=True, blank=True)
    duracion_minutos = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'Log de Tiempo'
        verbose_name_plural = 'Logs de Tiempo'
        ordering = ['fecha_inicio']

    def save(self, *args, **kwargs):
        if self.fecha_inicio and self.fecha_fin:
            delta = self.fecha_fin - self.fecha_inicio
            self.duracion_minutos = int(delta.total_seconds() / 60)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket.folio} - Pausa en '{self.estado_pausa}'"


class ConocimientoEntry(models.Model):
    titulo = models.CharField(max_length=300)
    descripcion_problema = models.TextField(blank=True, null=True)
    codigo_error = models.CharField(max_length=200, blank=True, null=True)
    solucion_aplicada = models.TextField(blank=True, null=True)
    causa_raiz = models.CharField(max_length=30, blank=True, null=True)
    sistema = models.ForeignKey(Sistema, on_delete=models.SET_NULL, null=True, blank=True, related_name='conocimiento')
    modulo = models.ForeignKey(Modulo, on_delete=models.SET_NULL, null=True, blank=True)
    ticket_origen = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True)
    veces_consultado = models.IntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Entrada de Conocimiento'
        verbose_name_plural = 'Base de Conocimiento'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.titulo
