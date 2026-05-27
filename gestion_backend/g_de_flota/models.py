import hashlib
import base64
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from cryptography.fernet import Fernet
from django.utils import timezone


# ─────────────────────────────────────────
# Cifrado Fernet
# ─────────────────────────────────────────

def _cipher() -> Fernet:
    key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

def cifrar(valor: str) -> str:
    return _cipher().encrypt(valor.encode()).decode()

def descifrar(valor: str) -> str:
    return _cipher().decrypt(valor.encode()).decode()

def normalizar_rut(rut: str) -> str:
    """12.345.678-9  →  12345678-9"""
    return rut.replace(".", "").strip().lower()


# ─────────────────────────────────────────
# Roles
# ─────────────────────────────────────────

class Rol(models.TextChoices):
    SUPERADMIN = "SUPERADMIN", "Super Administrador"
    USUARIO    = "USUARIO",    "Usuario"
    CONDUCTOR  = "CONDUCTOR",  "Conductor"


# ─────────────────────────────────────────
# Permisos granulares
# ─────────────────────────────────────────

class Permiso(models.Model):
    codigo    = models.CharField(max_length=100, unique=True)
    nombre    = models.CharField(max_length=200)
    categoria = models.CharField(max_length=50)

    class Meta:
        ordering         = ['categoria', 'codigo']
        verbose_name     = "Permiso"
        verbose_name_plural = "Permisos"

    def __str__(self):
        return f"{self.categoria} | {self.nombre}"


# ─────────────────────────────────────────
# Manager
# ─────────────────────────────────────────

class UsuarioManager(BaseUserManager):

    def _construir(self, email, password, rut=None, nombre_completo=None, **extra):
        if not email:
            raise ValueError("El email es obligatorio.")
        email = self.normalize_email(email)

        if rut:
            rut_norm = normalizar_rut(rut)
            extra["rut_hash"]    = hashlib.sha256(rut_norm.encode()).hexdigest()
            extra["rut_cifrado"] = cifrar(rut_norm)

        if nombre_completo:
            extra["nombre_cifrado"] = cifrar(nombre_completo)

        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, rut, nombre_completo, password=None, **extra):
        if not rut:
            raise ValueError("El RUT es obligatorio.")
        if not nombre_completo:
            raise ValueError("El nombre completo es obligatorio.")
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        extra.setdefault("rol", Rol.USUARIO)
        return self._construir(email, password, rut=rut, nombre_completo=nombre_completo, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("rol", Rol.SUPERADMIN)
        if extra.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        rut             = extra.pop("rut", None)
        nombre_completo = extra.pop("nombre_completo", None)
        return self._construir(email, password, rut=rut, nombre_completo=nombre_completo, **extra)


# ─────────────────────────────────────────
# Planes y Empresa
# ─────────────────────────────────────────

class PlanSuscripcion(models.Model):
    PLANES = [
        ('basico', 'Básico'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    nombre          = models.CharField(max_length=20, choices=PLANES, unique=True)
    descripcion     = models.CharField(max_length=500, blank=True, default='')
    precio_mensual  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_anual    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_flotas      = models.PositiveIntegerField(default=1)
    max_vehiculos   = models.PositiveIntegerField(default=10)
    max_conductores = models.PositiveIntegerField(default=10)
    max_usuarios    = models.PositiveIntegerField(default=5)
    modulos         = models.JSONField(default=list, blank=True)
    permisos        = models.ManyToManyField('Permiso', blank=True, related_name='planes')
    activo          = models.BooleanField(default=True)
    orden           = models.PositiveSmallIntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True, null=True)
    updated_at      = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering         = ['orden', 'id']
        verbose_name     = "Plan de Suscripción"
        verbose_name_plural = "Planes de Suscripción"

    def __str__(self):
        return self.get_nombre_display()


REGIONES_CHILE = [
    ('arica_y_parinacota', 'Arica y Parinacota'),
    ('tarapaca',           'Tarapacá'),
    ('antofagasta',        'Antofagasta'),
    ('atacama',            'Atacama'),
    ('coquimbo',           'Coquimbo'),
    ('valparaiso',         'Valparaíso'),
    ('metropolitana',      'Metropolitana'),
    ('ohiggins',           "O'Higgins"),
    ('maule',              'Maule'),
    ('nuble',              'Ñuble'),
    ('biobio',             'Biobío'),
    ('la_araucania',       'La Araucanía'),
    ('los_rios',           'Los Ríos'),
    ('los_lagos',          'Los Lagos'),
    ('aysen',              'Aysén'),
    ('magallanes',         'Magallanes'),
]

ESTADO_EMPRESA = [
    ('activa',     'Activa'),
    ('suspendida', 'Suspendida'),
]


class Empresa(models.Model):
    nombre            = models.CharField(max_length=255)
    rut_cifrado       = models.TextField(null=True, blank=True)
    rut_hash          = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    email_cifrado     = models.TextField(null=True, blank=True)
    telefono_cifrado  = models.TextField(null=True, blank=True)
    direccion_cifrada = models.TextField(null=True, blank=True)
    comuna_cifrada    = models.TextField(null=True, blank=True)
    ciudad_cifrada    = models.TextField(null=True, blank=True)
    region            = models.CharField(max_length=30, choices=REGIONES_CHILE, blank=True, default='')
    pais              = models.CharField(max_length=100, blank=True, default='Chile')
    estado            = models.CharField(max_length=20, choices=ESTADO_EMPRESA, default='activa')
    created_at        = models.DateTimeField(auto_now_add=True)
    plan              = models.ForeignKey(PlanSuscripcion, on_delete=models.SET_NULL, null=True, blank=True, related_name='empresas')

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    @property
    def rut(self) -> str | None:
        return descifrar(self.rut_cifrado) if self.rut_cifrado else None

    @property
    def email(self) -> str | None:
        return descifrar(self.email_cifrado) if self.email_cifrado else None

    @property
    def telefono(self) -> str | None:
        return descifrar(self.telefono_cifrado) if self.telefono_cifrado else None

    @property
    def direccion(self) -> str | None:
        return descifrar(self.direccion_cifrada) if self.direccion_cifrada else None

    @property
    def comuna(self) -> str | None:
        return descifrar(self.comuna_cifrada) if self.comuna_cifrada else None

    @property
    def ciudad(self) -> str | None:
        return descifrar(self.ciudad_cifrada) if self.ciudad_cifrada else None

    def set_rut(self, rut_plain: str):
        rut_norm = normalizar_rut(rut_plain)
        self.rut_cifrado = cifrar(rut_norm)
        self.rut_hash    = hashlib.sha256(rut_norm.encode()).hexdigest()

    def set_email(self, valor: str):
        self.email_cifrado = cifrar(valor)

    def set_telefono(self, valor: str):
        self.telefono_cifrado = cifrar(valor)

    def set_direccion(self, valor: str):
        self.direccion_cifrada = cifrar(valor)

    def set_comuna(self, valor: str):
        self.comuna_cifrada = cifrar(valor)

    def set_ciudad(self, valor: str):
        self.ciudad_cifrada = cifrar(valor)

    def __str__(self):
        return self.nombre


# ─────────────────────────────────────────
# Cambios de Plan (auditoría)
# ─────────────────────────────────────────

class CambioPlan(models.Model):
    empresa      = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cambios_plan')
    plan_antes   = models.ForeignKey(PlanSuscripcion, on_delete=models.SET_NULL, null=True, blank=True, related_name='cambios_salida')
    plan_despues = models.ForeignKey(PlanSuscripcion, on_delete=models.SET_NULL, null=True, blank=True, related_name='cambios_entrada')
    cambiado_por = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='cambios_plan')
    motivo       = models.CharField(max_length=500, blank=True, default='')
    fecha        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ['-fecha']
        verbose_name = "Cambio de Plan"
        verbose_name_plural = "Cambios de Plan"

    def __str__(self):
        antes  = self.plan_antes.get_nombre_display() if self.plan_antes else 'Sin plan'
        despues = self.plan_despues.get_nombre_display() if self.plan_despues else 'Sin plan'
        return f"{self.empresa.nombre}: {antes} → {despues}"


# ─────────────────────────────────────────
# Usuario  (autenticación)
# ─────────────────────────────────────────

class Usuario(AbstractUser):
    username   = None
    first_name = None
    last_name  = None

    email          = models.EmailField(unique=True)
    rut_cifrado    = models.TextField(null=True, blank=True)
    rut_hash       = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    nombre_cifrado = models.TextField(null=True, blank=True)
    rol            = models.CharField(max_length=20, choices=Rol.choices, default=Rol.USUARIO)
    empresa        = models.ForeignKey(
        Empresa, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='usuarios'
    )

    permisos = models.ManyToManyField(
        'Permiso', blank=True, related_name='usuarios'
    )

    # Datos integrados de conductor
    telefono_cifrado = models.TextField(null=True, blank=True)
    licencia_cifrada = models.TextField(null=True, blank=True)

    # Seguridad y Bloqueo
    intentos_fallidos = models.IntegerField(default=0)
    is_blocked        = models.BooleanField(default=False)

    # Preferencias de notificación
    # Estructura: {"inapp": ["mantencion","documentos","seguridad"], "email": ["mantencion","documentos"], "push_token": ""}
    notif_prefs = models.JSONField(default=dict, blank=True)

    politicas_aceptadas = models.BooleanField(default=False)
    primer_login        = models.BooleanField(default=True)

    # Datos adicionales (términos aceptados, etc.)
    extra = models.JSONField(default=dict, blank=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    @property
    def rut(self) -> str | None:
        return descifrar(self.rut_cifrado) if self.rut_cifrado else None

    @property
    def nombre(self) -> str | None:
        return descifrar(self.nombre_cifrado) if self.nombre_cifrado else None

    @property
    def telefono(self) -> str | None:
        return descifrar(self.telefono_cifrado) if self.telefono_cifrado else None

    @property
    def licencia(self) -> str | None:
        return descifrar(self.licencia_cifrada) if self.licencia_cifrada else None

    def set_rut(self, rut_plain: str):
        rut_norm = normalizar_rut(rut_plain)
        self.rut_cifrado = cifrar(rut_norm)
        self.rut_hash    = hashlib.sha256(rut_norm.encode()).hexdigest()

    def set_nombre(self, nombre_plain: str):
        self.nombre_cifrado = cifrar(nombre_plain)

    def set_telefono(self, valor: str):
        self.telefono_cifrado = cifrar(valor)

    def set_licencia(self, valor: str):
        self.licencia_cifrada = cifrar(valor)

    def __str__(self):
        return self.email


# ─────────────────────────────────────────
# Flota, Vehículo, Asignación
# ─────────────────────────────────────────

class Flota(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="flotas")
    nombre  = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre} ({self.empresa})"


class Vehiculo(models.Model):
    COMBUSTIBLE = [
        ('bencina',   'Bencina'),
        ('diesel',    'Diésel'),
        ('electrico', 'Eléctrico'),
        ('hibrido',   'Híbrido'),
    ]

    flota            = models.ForeignKey(Flota, on_delete=models.CASCADE, related_name="vehiculos")
    patente          = models.CharField(max_length=10, unique=True)
    marca            = models.CharField(max_length=100, blank=True, default='')
    modelo           = models.CharField(max_length=100, blank=True, default='')
    anio             = models.IntegerField(null=True, blank=True)
    tipo_combustible = models.CharField(max_length=20, choices=COMBUSTIBLE, default='bencina')
    km_actuales      = models.IntegerField(default=0)
    activo           = models.BooleanField(default=True)
    en_mantencion    = models.BooleanField(
        default=False,
        verbose_name='En mantención',
        help_text='True mientras el vehículo está fuera de servicio por una mantención activa.',
    )

    def __str__(self):
        return f"{self.patente} — {self.marca} {self.modelo}"


class Asignacion(models.Model):
    conductor = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="asignaciones_conductor",
        null=True, blank=True, limit_choices_to={'rol': Rol.CONDUCTOR}
    )
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name="asignaciones")
    activo   = models.BooleanField(default=True)
    desde    = models.DateTimeField(auto_now_add=True)
    hasta    = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['vehiculo'],
                condition=models.Q(activo=True),
                name='unique_active_vehicle_assignment'
            ),
            models.UniqueConstraint(
                fields=['conductor'],
                condition=models.Q(activo=True),
                name='unique_active_conductor_assignment'
            )
        ]




# ─────────────────────────────────────────
# Mantenimiento y auditoría
# ─────────────────────────────────────────

class EstadoMantencion(models.TextChoices):
    PENDIENTE  = 'pendiente',  'Pendiente'
    EN_PROCESO = 'en_proceso', 'En Proceso'
    REALIZADA  = 'realizada',  'Realizada'
    CANCELADA  = 'cancelada',  'Cancelada'


class Mantencion(models.Model):
    vehiculo               = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name="mantenciones")
    tipo_mantencion        = models.CharField(max_length=100)
    descripcion            = models.TextField(blank=True, default='')
    taller_proveedor       = models.CharField(max_length=200, blank=True, default='')
    presupuesto            = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    fecha_programada       = models.DateField(null=True, blank=True)
    kilometraje_programado = models.IntegerField(null=True, blank=True)

    fecha_realizada        = models.DateField(null=True, blank=True)
    kilometraje_realizado  = models.IntegerField(null=True, blank=True)

    estado                 = models.CharField(max_length=50, choices=EstadoMantencion.choices, default=EstadoMantencion.PENDIENTE)
    costo                  = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # ── Comprobante y confirmación del conductor ───────────────────────────────
    foto_comprobante       = models.ImageField(
        upload_to='mantenciones/comprobantes/',
        null=True, blank=True,
        verbose_name='Foto comprobante',
        help_text='Foto del recibo o trabajo realizado, subida al completar la mantención.',
    )
    confirmado_conductor   = models.BooleanField(
        default=False,
        verbose_name='Confirmado por conductor',
        help_text='True cuando el conductor acepta el servicio y el precio final.',
    )
    fecha_confirmacion     = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Fecha de confirmación',
    )


class TipoLog(models.TextChoices):
    SEGURIDAD = 'SEGURIDAD', 'Seguridad'
    ACTIVIDAD = 'ACTIVIDAD', 'Actividad'


class LogAuditoria(models.Model):
    tipo    = models.CharField(max_length=20, choices=TipoLog.choices)
    accion  = models.CharField(max_length=50)
    usuario = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='logs_auditoria'
    )
    detalle    = models.JSONField(default=dict, blank=True)
    ip         = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    so         = models.CharField(max_length=30, null=True, blank=True)   # Sistema operativo
    metodo     = models.CharField(max_length=10, null=True, blank=True)   # Método HTTP
    endpoint   = models.CharField(max_length=300, null=True, blank=True)  # URL path
    fecha      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"

    def __str__(self):
        return f"{self.tipo} | {self.accion} | {self.fecha}"


# ─────────────────────────────────────────
# Notificaciones
# ─────────────────────────────────────────

NOTIF_PREFS_DEFAULT = {
    "inapp": ["mantencion", "documentos", "seguridad"],
    "email": ["mantencion", "documentos"],
    "push_token": "",
}

TIPO_NOTIF_CATEGORIA = {
    "mantencion_por_vencer": "mantencion",
    "mantencion_vencida":    "mantencion",
    "documento_por_vencer":  "documentos",
    "documento_vencido":     "documentos",
    "seguridad":             "seguridad",
    "actividad":             "actividad",
    "limite_plan":           "seguridad",
}


class TipoNotificacion(models.TextChoices):
    MANTENCION_POR_VENCER = "mantencion_por_vencer", "Mantención por vencer"
    MANTENCION_VENCIDA    = "mantencion_vencida",    "Mantención vencida"
    DOCUMENTO_POR_VENCER  = "documento_por_vencer",  "Documento por vencer"
    DOCUMENTO_VENCIDO     = "documento_vencido",     "Documento vencido"
    SEGURIDAD             = "seguridad",             "Seguridad"
    ACTIVIDAD             = "actividad",             "Actividad"
    LIMITE_PLAN           = "limite_plan",           "Límite de plan"


class Notificacion(models.Model):
    usuario    = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='notificaciones')
    tipo       = models.CharField(max_length=30, choices=TipoNotificacion.choices)
    titulo     = models.CharField(max_length=200)
    mensaje    = models.TextField()
    leida      = models.BooleanField(default=False)
    url_accion = models.CharField(max_length=300, blank=True, default='')
    extra      = models.JSONField(default=dict, blank=True)
    fecha      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return f"{self.tipo} → {self.usuario_id} | {self.fecha}"


# ─────────────────────────────────────────
# Mantenimiento Predictivo
# ─────────────────────────────────────────

class PlanMantenimiento(models.Model):
    empresa     = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="planes_mantenimiento")
    nombre      = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    activo      = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"


class ReglaMantenimiento(models.Model):
    PRIORIDADES = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
    ]
    CANALES = [
        ('email', 'Email'),
        ('push', 'Push'),
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
    ]
    plan                  = models.ForeignKey(PlanMantenimiento, on_delete=models.CASCADE, related_name="reglas")
    tipo                  = models.CharField(max_length=100)
    prioridad             = models.CharField(max_length=20, choices=PRIORIDADES, default='media')
    intervalo_dias        = models.IntegerField()
    umbral_alerta_dias    = models.IntegerField()
    canal                 = models.CharField(max_length=20, choices=CANALES, default='email')
    escalar_sin_respuesta = models.BooleanField(default=False)
    bloquear_despacho     = models.BooleanField(default=False)
    costo_estimado        = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.tipo} - Cada {self.intervalo_dias} días"


class VehiculoPlan(models.Model):
    vehiculo         = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name="planes_asignados")
    plan             = models.ForeignKey(PlanMantenimiento, on_delete=models.CASCADE, related_name="vehiculos_asignados")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vehiculo', 'plan')


class MantencionProgramada(models.Model):
    ESTADOS = [
        ('activa', 'Activa'),
        ('inactiva', 'Inactiva'),
    ]
    vehiculo        = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name="mantenciones_programadas")
    regla           = models.ForeignKey(ReglaMantenimiento, on_delete=models.CASCADE, related_name="mantenciones_programadas")
    fecha_ultima    = models.DateField()
    fecha_siguiente = models.DateField()
    estado          = models.CharField(max_length=20, choices=ESTADOS, default='activa')

    def __str__(self):
        return f"{self.regla.tipo} para {self.vehiculo.patente}"


class AlertaMantencion(models.Model):
    NIVELES = [
        ('por_vencer', 'Por vencer'),
        ('vencida', 'Vencida'),
    ]
    mantencion_programada = models.ForeignKey(MantencionProgramada, on_delete=models.CASCADE, related_name="alertas")
    nivel                 = models.CharField(max_length=20, choices=NIVELES)
    dias_restantes        = models.IntegerField()
    pct_avance            = models.FloatField()
    enviada               = models.BooleanField(default=False)
    atendida              = models.BooleanField(default=False)
    fecha_creacion        = models.DateTimeField(auto_now_add=True)
    fecha_atencion        = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.nivel} - {self.mantencion_programada}"


# ─────────────────────────────────────────
# Finanzas operativas
# ─────────────────────────────────────────

class GastoOperativo(models.Model):
    CATEGORIAS = [
        ('combustible', 'Combustible'),
        ('mantencion',  'Mantención'),
        ('multa',       'Multa'),
        ('peaje',       'Peaje'),
        ('seguro',      'Seguro'),
        ('otro',        'Otro'),
    ]
    empresa        = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='gastos')
    vehiculo       = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True)
    conductor      = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='gastos_conductor')
    categoria      = models.CharField(max_length=20, choices=CATEGORIAS)
    descripcion    = models.CharField(max_length=300)
    monto          = models.DecimalField(max_digits=10, decimal_places=0)
    fecha          = models.DateField()
    comprobante    = models.FileField(upload_to='comprobantes/', null=True, blank=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='gastos_registrados')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha', '-created_at']
        verbose_name = 'Gasto operativo'

    def __str__(self):
        return f"{self.get_categoria_display()} ${self.monto} — {self.fecha}"


class PresupuestoMensual(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='presupuestos')
    anio    = models.PositiveSmallIntegerField()
    mes     = models.PositiveSmallIntegerField()
    monto   = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        unique_together = ('empresa', 'anio', 'mes')
        verbose_name = 'Presupuesto mensual'

    def __str__(self):
        return f"{self.empresa.nombre} — {self.mes}/{self.anio}: ${self.monto}"


class Documento(models.Model):
    TIPOS_VEHICULO = [
        ('permiso_circulacion', 'Permiso de circulación'),
        ('revision_tecnica',    'Revisión técnica'),
        ('seguro_soap',         'Seguro SOAP'),
    ]
    TIPOS_CONDUCTOR = [
        ('licencia',     'Licencia de conducir'),
        ('antecedentes', 'Antecedentes comerciales'),
    ]
    TODOS_TIPOS = TIPOS_VEHICULO + TIPOS_CONDUCTOR

    ENTIDADES = [
        ('vehiculo',  'Vehículo'),
        ('conductor', 'Conductor'),
    ]

    empresa   = models.ForeignKey(Empresa,  on_delete=models.CASCADE, related_name='documentos')
    entidad   = models.CharField(max_length=20, choices=ENTIDADES)
    tipo      = models.CharField(max_length=30, choices=TODOS_TIPOS)

    vehiculo  = models.ForeignKey(Vehiculo, on_delete=models.CASCADE,
                                  null=True, blank=True, related_name='docs_v')
    conductor = models.ForeignKey(Usuario,  on_delete=models.CASCADE,
                                  null=True, blank=True, related_name='docs_c')

    fecha_emision     = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    archivo        = models.FileField(upload_to='documentos/%Y/%m/', null=True, blank=True)
    nombre_archivo = models.CharField(max_length=200, blank=True, default='')

    subido_por       = models.ForeignKey(Usuario, on_delete=models.SET_NULL,
                                         null=True, related_name='docs_subidos')
    notas            = models.CharField(max_length=500, blank=True, default='')
    version_anterior = models.ForeignKey('self', on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='versiones_nuevas')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ['-created_at']
        verbose_name = 'Documento'

    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        delta = self.fecha_vencimiento - timezone.now().date()
        return delta.days

    def estado(self):
        dias = self.dias_para_vencer()
        if dias is None:
            return 'sin_vencimiento'
        if dias < 0:
            return 'vencido'
        if dias <= 30:
            return 'por_vencer'
        return 'vigente'

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.empresa.nombre}"


# ─────────────────────────────────────────
# Módulo de Rutas y Trabajos
# ─────────────────────────────────────────

class Ruta(models.Model):
    TIPOS = [
        ('carga',    'Carga'),
        ('personas', 'Personas'),
    ]
    ESTADOS = [
        ('borrador',   'Borrador'),
        ('pendiente',  'Pendiente'),
        ('activo',     'Activo'),
        ('finalizado', 'Finalizado'),
        ('cancelado',  'Cancelado'),
    ]
    empresa           = models.ForeignKey(Empresa,  on_delete=models.CASCADE, related_name='rutas')
    tipo              = models.CharField(max_length=20, choices=TIPOS, default='carga')
    nombre            = models.CharField(max_length=200)
    descripcion       = models.TextField(blank=True, default='')
    estado            = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    conductor         = models.ForeignKey(Usuario,  on_delete=models.SET_NULL, null=True, blank=True, related_name='rutas_conductor')
    vehiculo          = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True, related_name='rutas')
    fecha_programada  = models.DateField(null=True, blank=True)
    hora_programada   = models.TimeField(null=True, blank=True, help_text='Hora de inicio programada')
    fecha_inicio      = models.DateTimeField(null=True, blank=True)
    fecha_fin         = models.DateTimeField(null=True, blank=True)
    km_inicio         = models.IntegerField(null=True, blank=True)
    km_fin            = models.IntegerField(null=True, blank=True)
    distancia_km      = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    duracion_min      = models.IntegerField(null=True, blank=True)
    polyline          = models.JSONField(default=list, blank=True)
    notas             = models.TextField(blank=True, default='')
    extra             = models.JSONField(default=dict, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ['-created_at']
        verbose_name = 'Ruta'
        verbose_name_plural = 'Rutas'

    @property
    def km_reales(self):
        if self.km_inicio is not None and self.km_fin is not None:
            return self.km_fin - self.km_inicio
        return None

    def __str__(self):
        return f"{self.nombre} ({self.get_estado_display()})"


class Parada(models.Model):
    TIPOS = [
        ('origen',  'Origen'),
        ('parada',  'Parada'),
        ('destino', 'Destino'),
    ]
    ruta           = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name='paradas')
    tipo           = models.CharField(max_length=20, choices=TIPOS, default='parada')
    orden          = models.PositiveSmallIntegerField(default=0)
    nombre         = models.CharField(max_length=200)
    direccion      = models.CharField(max_length=400, blank=True, default='')
    latitud        = models.FloatField(null=True, blank=True)
    longitud       = models.FloatField(null=True, blank=True)
    notas          = models.CharField(max_length=400, blank=True, default='')
    hora_estimada  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering     = ['orden']
        verbose_name = 'Parada'

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.nombre}"


class EventoRuta(models.Model):
    """Historial de eventos automáticos y comentarios manuales de una ruta."""
    TIPO_CHOICES = [
        ('auto',       'Automático'),
        ('comentario', 'Comentario'),
    ]
    ruta       = models.ForeignKey(Ruta,    on_delete=models.CASCADE,  related_name='eventos')
    tipo       = models.CharField(max_length=20, choices=TIPO_CHOICES, default='comentario')
    texto      = models.TextField()
    autor      = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='eventos_ruta'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ['created_at']
        verbose_name = 'Evento de Ruta'

    def __str__(self):
        return f"[{self.tipo}] {self.ruta.nombre} — {self.texto[:50]}"


# ─────────────────────────────────────────
# Solicitudes de Conductores
# ─────────────────────────────────────────

class SolicitudConductor(models.Model):
    TIPOS = [
        ('mantencion',  'Mantención'),
        ('combustible', 'Combustible'),
        ('incidencia',  'Incidencia'),
        ('documento',   'Documento'),
    ]
    ESTADOS = [
        ('pendiente',   'Pendiente'),
        ('en_revision', 'En revisión'),
        ('aprobado',    'Aprobado'),
        ('rechazado',   'Rechazado'),
    ]
    PRIORIDADES = [
        ('baja',  'Baja'),
        ('media', 'Media'),
        ('alta',  'Alta'),
    ]

    empresa        = models.ForeignKey(
        Empresa, on_delete=models.CASCADE,
        related_name='solicitudes_conductores', null=True, blank=True,
    )
    conductor      = models.ForeignKey(
        Usuario, on_delete=models.CASCADE,
        related_name='solicitudes_conductor',
        limit_choices_to={'rol': Rol.CONDUCTOR},
    )
    vehiculo       = models.ForeignKey(
        Vehiculo, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='solicitudes_vehiculo',
    )
    tipo           = models.CharField(max_length=20, choices=TIPOS)
    titulo         = models.CharField(max_length=200)
    descripcion    = models.TextField(blank=True, default='')
    estado         = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    prioridad      = models.CharField(max_length=10, choices=PRIORIDADES, default='media')
    foto           = models.FileField(upload_to='solicitudes/%Y/%m/', null=True, blank=True)
    respuesta      = models.TextField(blank=True, default='')
    extra          = models.JSONField(default=dict, blank=True)
    respondido_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='solicitudes_respondidas',
    )
    respondido_at  = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ['-created_at']
        verbose_name = 'Solicitud de Conductor'
        verbose_name_plural = 'Solicitudes de Conductores'

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.conductor} — {self.get_estado_display()}"


# ─────────────────────────────────────────
# Configuración global del sistema (singleton)
# ─────────────────────────────────────────

class ConfiguracionSistema(models.Model):
    """Singleton. Acceder siempre vía ConfiguracionSistema.get()."""

    # Términos y condiciones
    terminos_condiciones   = models.TextField(blank=True, default='')
    terminos_version       = models.CharField(max_length=20, blank=True, default='1.0')
    terminos_updated_at    = models.DateTimeField(null=True, blank=True)

    # Configuración de trial y pagos
    dias_trial             = models.PositiveSmallIntegerField(default=14)
    dias_gracia_pago       = models.PositiveSmallIntegerField(default=7)
    bloqueo_automatico     = models.BooleanField(default=True)
    mensaje_pago_pendiente = models.TextField(
        blank=True,
        default='Tu suscripción tiene un pago pendiente. Por favor regulariza tu situación para continuar usando el servicio.'
    )

    class Meta:
        verbose_name        = 'Configuración del Sistema'
        verbose_name_plural = 'Configuración del Sistema'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Configuración del Sistema'


# ─────────────────────────────────────────
# Suscripciones y pagos Transbank
# ─────────────────────────────────────────

class Suscripcion(models.Model):
    ESTADOS = [
        ('pendiente',  'Pendiente de pago'),
        ('activa',     'Activa'),
        ('gracia',     'Período de gracia'),
        ('suspendida', 'Suspendida'),
        ('cancelada',  'Cancelada'),
    ]
    CICLOS = [('mensual', 'Mensual'), ('anual', 'Anual')]

    empresa           = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='suscripcion')
    plan              = models.ForeignKey(PlanSuscripcion, on_delete=models.PROTECT)
    ciclo             = models.CharField(max_length=10, choices=CICLOS, default='mensual')
    estado            = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_inicio      = models.DateTimeField(null=True, blank=True)
    fecha_fin_periodo = models.DateTimeField(null=True, blank=True)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    dias_gracia       = models.PositiveSmallIntegerField(default=7)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Suscripción'

    @property
    def esta_bloqueada(self):
        # Pendiente = sin primer pago; suspendida/cancelada = acceso revocado
        return self.estado in ('pendiente', 'suspendida', 'cancelada')

    @property
    def dias_para_vencer(self):
        if not self.fecha_fin_periodo:
            return None
        return (self.fecha_fin_periodo.date() - timezone.now().date()).days

    def __str__(self):
        return f"{self.empresa.nombre} — {self.get_estado_display()}"


class PagoTransbank(models.Model):
    ESTADOS = [
        ('iniciado',  'Iniciado'),
        ('aprobado',  'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('anulado',   'Anulado'),
        ('fallido',   'Fallido'),
    ]

    empresa      = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='pagos')
    suscripcion  = models.ForeignKey(Suscripcion, on_delete=models.PROTECT, related_name='pagos')
    token        = models.CharField(max_length=200, unique=True)
    orden_compra = models.CharField(max_length=64, unique=True)
    monto        = models.PositiveIntegerField()
    estado       = models.CharField(max_length=20, choices=ESTADOS, default='iniciado')
    ciclo        = models.CharField(max_length=10, default='mensual')
    plan_nombre  = models.CharField(max_length=50, blank=True, default='')
    respuesta_tb = models.JSONField(default=dict, blank=True)
    fecha_pago   = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ['-created_at']
        verbose_name = 'Pago Transbank'

    def __str__(self):
        return f"{self.empresa.nombre} — {self.orden_compra} — {self.get_estado_display()}"


# ─────────────────────────────────────────
# Tarjeta guardada – Webpay OneClick Mall
# ─────────────────────────────────────────

class TarjetaGuardada(models.Model):
    """
    Tarjeta inscrita con Webpay OneClick para cobros automáticos.
    Se crea cuando el usuario completa el formulario de inscripción de OneClick.
    """
    empresa     = models.OneToOneField(
        Empresa, on_delete=models.CASCADE, related_name='tarjeta_guardada'
    )
    tbk_user    = models.CharField(max_length=200)        # token de cobro devuelto por Transbank
    username_tb = models.CharField(max_length=100)        # identificador usado en la inscripción
    last_4      = models.CharField(max_length=4,  blank=True)
    card_type   = models.CharField(max_length=40, blank=True)   # Visa, MasterCard, etc.
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Tarjeta guardada'
        verbose_name_plural = 'Tarjetas guardadas'

    def __str__(self):
        return f"{self.empresa.nombre} – {self.card_type} ****{self.last_4}"