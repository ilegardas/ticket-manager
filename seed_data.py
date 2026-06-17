"""
Run with: DJANGO_SETTINGS_MODULE=config.settings python seed_data.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tickets.models import (
    Usuario, Sistema, Modulo, Prioridad, Estado, Categoria, Ticket, ChatterEntry
)
from django.utils import timezone

print("Seeding initial data...")

# Prioridades
prioridades_data = [
    {'nombre': 'Crítica', 'sla_horas': 4, 'color': '#EF4444', 'orden': 1},
    {'nombre': 'Alta', 'sla_horas': 8, 'color': '#F97316', 'orden': 2},
    {'nombre': 'Media', 'sla_horas': 24, 'color': '#EAB308', 'orden': 3},
    {'nombre': 'Baja', 'sla_horas': 72, 'color': '#22C55E', 'orden': 4},
]
for p in prioridades_data:
    Prioridad.objects.get_or_create(nombre=p['nombre'], defaults=p)
print(f"  Prioridades: {Prioridad.objects.count()}")

# Estados
estados_data = [
    {'nombre': 'Nuevo', 'es_estado_cierre': False, 'pausa_sla': False, 'color': '#3B82F6', 'orden': 1},
    {'nombre': 'Asignado', 'es_estado_cierre': False, 'pausa_sla': False, 'color': '#8B5CF6', 'orden': 2},
    {'nombre': 'En Proceso', 'es_estado_cierre': False, 'pausa_sla': False, 'color': '#F97316', 'orden': 3},
    {'nombre': 'En Espera de Usuario', 'es_estado_cierre': False, 'pausa_sla': True, 'color': '#EAB308', 'orden': 4},
    {'nombre': 'En Revisión', 'es_estado_cierre': False, 'pausa_sla': True, 'color': '#6366F1', 'orden': 5},
    {'nombre': 'Resuelto', 'es_estado_cierre': False, 'pausa_sla': False, 'color': '#10B981', 'orden': 6},
    {'nombre': 'Cerrado', 'es_estado_cierre': True, 'pausa_sla': False, 'color': '#6B7280', 'orden': 7},
    {'nombre': 'Cancelado', 'es_estado_cierre': True, 'pausa_sla': False, 'color': '#9CA3AF', 'orden': 8},
]
for e in estados_data:
    Estado.objects.get_or_create(nombre=e['nombre'], defaults=e)
print(f"  Estados: {Estado.objects.count()}")

# Categorias
categorias_data = [
    {'nombre': 'Acceso / Permisos', 'color': '#6366F1'},
    {'nombre': 'Error de Sistema', 'color': '#EF4444'},
    {'nombre': 'Configuración', 'color': '#F97316'},
    {'nombre': 'Consulta / Información', 'color': '#3B82F6'},
    {'nombre': 'Requerimiento de Mejora', 'color': '#8B5CF6'},
    {'nombre': 'Capacitación', 'color': '#10B981'},
    {'nombre': 'Reportes', 'color': '#EAB308'},
    {'nombre': 'Integración', 'color': '#EC4899'},
]
for c in categorias_data:
    Categoria.objects.get_or_create(nombre=c['nombre'], defaults=c)
print(f"  Categorias: {Categoria.objects.count()}")

# Sistemas
sistemas_data = [
    {'nombre': 'SIGED', 'descripcion': 'Sistema de Gestión Educativa', 'version': '3.2', 'proveedor': 'SEECH'},
    {'nombre': 'SAPASE', 'descripcion': 'Sistema de Administración de Personal y Servicios Educativos', 'version': '2.1', 'proveedor': 'SEECH'},
    {'nombre': 'SIFETE', 'descripcion': 'Sistema de Finanzas y Tesorería', 'version': '1.5', 'proveedor': 'Externo'},
    {'nombre': 'Portal Educativo', 'descripcion': 'Portal web de recursos educativos', 'version': '4.0', 'proveedor': 'SEECH'},
    {'nombre': 'SIIE', 'descripcion': 'Sistema de Información e Indicadores Educativos', 'version': '2.0', 'proveedor': 'SEP'},
    {'nombre': 'Correo Institucional', 'descripcion': 'Sistema de correo electrónico institucional', 'version': None, 'proveedor': 'Google Workspace'},
]
for s in sistemas_data:
    obj, created = Sistema.objects.get_or_create(nombre=s['nombre'], defaults=s)
    if created:
        # Create some modules for each system
        modulos = []
        if s['nombre'] == 'SIGED':
            modulos = ['Inscripciones', 'Calificaciones', 'Boletas', 'Estadística Educativa', 'Historial Académico']
        elif s['nombre'] == 'SAPASE':
            modulos = ['Nómina', 'Recursos Humanos', 'Asistencia', 'Licencias y Permisos']
        elif s['nombre'] == 'SIFETE':
            modulos = ['Presupuesto', 'Pagos', 'Facturación', 'Contabilidad']
        elif s['nombre'] == 'Portal Educativo':
            modulos = ['Contenidos', 'Usuarios', 'Biblioteca Digital', 'Foros']
        for m in modulos:
            Modulo.objects.get_or_create(nombre=m, sistema=obj)
print(f"  Sistemas: {Sistema.objects.count()}")
print(f"  Modulos: {Modulo.objects.count()}")

# Superuser / Admin
if not Usuario.objects.filter(correo_electronico='admin@seech.gob.mx').exists():
    admin = Usuario.objects.create_superuser(
        correo_electronico='admin@seech.gob.mx',
        nombre_completo='Administrador SEECH',
        password='seech2024',
        rol='admin',
    )
    print(f"  Admin user created: admin@seech.gob.mx / seech2024")
else:
    admin = Usuario.objects.get(correo_electronico='admin@seech.gob.mx')
    print(f"  Admin user already exists")

# Sample technician
if not Usuario.objects.filter(correo_electronico='tecnico@seech.gob.mx').exists():
    tecnico = Usuario.objects.create_user(
        correo_electronico='tecnico@seech.gob.mx',
        nombre_completo='Carlos Rodríguez Méndez',
        password='seech2024',
        rol='tecnico',
        numero_empleado='T001',
        puesto_cargo='Técnico de Soporte',
        region_zona='Zona Centro',
    )
    print(f"  Técnico user created: tecnico@seech.gob.mx / seech2024")
else:
    tecnico = Usuario.objects.get(correo_electronico='tecnico@seech.gob.mx')

# Sample reporting user
if not Usuario.objects.filter(correo_electronico='reporta@seech.gob.mx').exists():
    reporta = Usuario.objects.create_user(
        correo_electronico='reporta@seech.gob.mx',
        nombre_completo='María González López',
        password='seech2024',
        rol='usuario',
        numero_empleado='U001',
        puesto_cargo='Docente',
        cct='08DPR0001A',
        region_zona='Zona Norte',
        nivel_educativo='Primaria',
    )
    print(f"  User created: reporta@seech.gob.mx / seech2024")
else:
    reporta = Usuario.objects.get(correo_electronico='reporta@seech.gob.mx')

# Sample tickets
if Ticket.objects.count() == 0:
    estado_nuevo = Estado.objects.get(nombre='Nuevo')
    estado_proceso = Estado.objects.get(nombre='En Proceso')
    estado_espera = Estado.objects.get(nombre='En Espera de Usuario')
    estado_cerrado = Estado.objects.get(nombre='Cerrado')
    prio_critica = Prioridad.objects.get(nombre='Crítica')
    prio_alta = Prioridad.objects.get(nombre='Alta')
    prio_media = Prioridad.objects.get(nombre='Media')
    prio_baja = Prioridad.objects.get(nombre='Baja')
    cat_error = Categoria.objects.get(nombre='Error de Sistema')
    cat_acceso = Categoria.objects.get(nombre='Acceso / Permisos')
    cat_consulta = Categoria.objects.get(nombre='Consulta / Información')
    siged = Sistema.objects.get(nombre='SIGED')
    sapase = Sistema.objects.get(nombre='SAPASE')

    tickets_data = [
        {
            'titulo': 'No se pueden generar boletas en SIGED',
            'descripcion': 'Al intentar generar las boletas del ciclo escolar, el sistema muestra un error 500.',
            'sistema': siged, 'modulo': Modulo.objects.get(nombre='Boletas'),
            'prioridad': prio_critica, 'estado': estado_proceso,
            'categoria': cat_error, 'usuario_reporta': reporta, 'usuario_asignado': tecnico,
            'codigo_error': 'ERR-500-BOLETAS',
            'impacto_proceso': 'caido_total',
            'fecha_asignacion': timezone.now(),
        },
        {
            'titulo': 'Error de acceso en módulo de nómina SAPASE',
            'descripcion': 'Los usuarios del departamento de RRHH no pueden acceder al módulo de nómina.',
            'sistema': sapase, 'modulo': Modulo.objects.get(nombre='Nómina'),
            'prioridad': prio_alta, 'estado': estado_nuevo,
            'categoria': cat_acceso, 'usuario_reporta': reporta, 'usuario_asignado': None,
            'impacto_proceso': 'parcial',
        },
        {
            'titulo': 'Consulta sobre exportación de estadísticas',
            'descripcion': 'Necesito saber cómo exportar el reporte de estadística educativa a Excel.',
            'sistema': siged, 'modulo': Modulo.objects.get(nombre='Estadística Educativa'),
            'prioridad': prio_baja, 'estado': estado_espera,
            'categoria': cat_consulta, 'usuario_reporta': reporta, 'usuario_asignado': tecnico,
            'impacto_proceso': 'funcional',
        },
        {
            'titulo': 'Sistema SIGED lento en horario de reporte',
            'descripcion': 'Entre las 8am y 10am el sistema se vuelve muy lento.',
            'sistema': siged, 'prioridad': prio_media, 'estado': estado_proceso,
            'categoria': cat_error, 'usuario_reporta': reporta, 'usuario_asignado': tecnico,
            'impacto_proceso': 'parcial',
            'fecha_asignacion': timezone.now(),
        },
        {
            'titulo': 'Solicitud de acceso a módulo de Licencias',
            'descripcion': 'Requiero acceso al módulo de Licencias y Permisos en SAPASE.',
            'sistema': sapase, 'modulo': Modulo.objects.get(nombre='Licencias y Permisos'),
            'prioridad': prio_baja, 'estado': estado_cerrado,
            'categoria': cat_acceso, 'usuario_reporta': reporta, 'usuario_asignado': tecnico,
            'solucion_aplicada': 'Se otorgaron los permisos correspondientes al perfil del usuario.',
            'calificacion_estrellas': 5,
            'tiempo_atencion_minutos': 45,
            'fecha_asignacion': timezone.now(),
            'fecha_resolucion': timezone.now(),
            'fecha_cierre': timezone.now(),
        },
    ]

    for t_data in tickets_data:
        ticket = Ticket.objects.create(**t_data)
        ChatterEntry.objects.create(
            ticket=ticket,
            tipo='sistema',
            autor=admin,
            contenido=f"Ticket creado con folio {ticket.folio}",
        )
        if ticket.usuario_asignado:
            ChatterEntry.objects.create(
                ticket=ticket,
                tipo='asignacion',
                autor=admin,
                contenido=f"Ticket asignado a {ticket.usuario_asignado.nombre_completo}",
            )

    print(f"  Tickets: {Ticket.objects.count()}")

print("\nSeed completado.")
print("\nCredenciales:")
print("  Admin:   admin@seech.gob.mx / seech2024")
print("  Técnico: tecnico@seech.gob.mx / seech2024")
print("  Usuario: reporta@seech.gob.mx / seech2024")
