from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Sistema, Modulo, Documento, Prioridad, Estado, Categoria,
    Ticket, ChatterEntry, TicketTimeLog, ConocimientoEntry, Token
)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['correo_electronico', 'nombre_completo', 'rol', 'activo']
    list_filter = ['rol', 'activo', 'nivel_educativo', 'region_zona']
    search_fields = ['correo_electronico', 'nombre_completo', 'numero_empleado']
    ordering = ['nombre_completo']
    fieldsets = (
        (None, {'fields': ('correo_electronico', 'password')}),
        ('Información Personal', {'fields': ('nombre_completo', 'numero_empleado', 'puesto_cargo', 'cct', 'region_zona', 'nivel_educativo')}),
        ('Permisos', {'fields': ('rol', 'activo', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('correo_electronico', 'nombre_completo', 'password1', 'password2', 'rol'),
        }),
    )


@admin.register(Sistema)
class SistemaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'version', 'proveedor', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'proveedor']


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    # 🚀 1. Quitamos 'sistema' de list_display y agregamos un método personalizado
    list_display = ('id', 'nombre', 'ver_sistemas', 'activo', 'fecha_creacion') 
    
    # 🚀 2. Eliminamos 'sistema' de list_filter ya que causaba el error E116
    list_filter = ('activo', 'fecha_creacion')
    
    search_fields = ('nombre', 'descripcion')

    # 🎯 3. Método auxiliar para mostrar los sistemas asociados en la tabla del admin
    def ver_sistemas(self, obj):
        # Buscamos todos los sistemas asociados a este módulo usando la relación inversa (related_name='sistemas')
        sistemas_asociados = obj.sistemas.all()
        if sistemas_asociados:
            return ", ".join([s.nombre for s in sistemas_asociados])
        return "—"
    
    # Nombre que saldrá en la cabecera de la columna en el panel
    ver_sistemas.short_description = "Sistemas Asociados"


@admin.register(Prioridad)
class PrioridadAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'sla_horas', 'color', 'orden']
    ordering = ['orden']


@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'es_estado_cierre', 'pausa_sla', 'color', 'orden']
    ordering = ['orden']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'color']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['folio', 'titulo', 'estado', 'prioridad', 'usuario_asignado', 'fecha_creacion']
    list_filter = ['estado', 'prioridad', 'categoria', 'sistema', 'ticket_reabierto']
    search_fields = ['folio', 'titulo', 'descripcion']
    raw_id_fields = ['sistema', 'modulo', 'usuario_reporta', 'usuario_asignado']
    readonly_fields = ['folio', 'fecha_creacion', 'tiempo_atencion_minutos']


@admin.register(ChatterEntry)
class ChatterAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'tipo', 'autor', 'fecha_creacion']
    list_filter = ['tipo']


@admin.register(ConocimientoEntry)
class ConocimientoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'codigo_error', 'causa_raiz', 'sistema', 'veces_consultado']
    search_fields = ['titulo', 'codigo_error', 'solucion_aplicada']
    list_filter = ['causa_raiz', 'sistema']


admin.site.register(Documento)
admin.site.register(TicketTimeLog)
admin.site.register(Token)
