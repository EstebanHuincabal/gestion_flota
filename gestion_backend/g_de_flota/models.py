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


class DocumentoBase(models.Model):
    ESTADOS = [
        ('vigente',    'Vigente'),
        ('por_vencer', 'Por vencer'),
        ('vencido',    'Vencido'),
    ]
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='vigente')

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        hoy  = timezone.now().date()
        dias = (self.fecha_vencimiento - hoy).days
        self.estado = 'vencido' if dias < 0 else 'por_vencer' if dias <= 30 else 'vigente'
        super().save(*args, **kwargs)


class DocumentoConductor(DocumentoBase):
    TIPOS = [
        ('licencia_conducir', 'Licencia de Conducir'),
        ('certificado_salud', 'Certificado de Salud'),
        ('antecedentes',      'Antecedentes'),
        ('otro',              'Otro'),
    ]
    conductor         = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='documentos_conductor', null=True, blank=True)
    tipo              = models.CharField(max_length=30, choices=TIPOS, default='otro')
    numero            = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        ordering         = ['fecha_vencimiento']
        verbose_name     = "Documento del Conductor"
        verbose_name_plural = "Documentos de Conductores"

    def __str__(self):
        email = self.conductor.email if self.conductor else "Desconocido"
        return f"{self.get_tipo_display()} — {email}"


# ─────────────────────────────────────────
# Telemetría y gestión
# ─────────────────────────────────────────

class Ubicacion(models.Model):
    vehiculo    = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name="ubicaciones")
    latitud     = models.FloatField()
    longitud    = models.FloatField()
    velocidad   = models.FloatField()
    combustible = models.FloatField()
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]


class Evento(models.Model):
    vehiculo    = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name="eventos")
    tipo        = models.CharField(max_length=100)
    descripcion = models.TextField()
    fecha       = models.DateTimeField(auto_now_add=True)


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


class DocumentoVehiculo(DocumentoBase):
    TIPOS = [
        ('permiso_circulacion', 'Permiso de Circulación'),
        ('seguro',              'Seguro (SOAP)'),
        ('revision_tecnica',   'Revisión Técnica'),
        ('otro',               'Otro'),
    ]

    vehiculo          = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name="documentos")
    tipo              = models.CharField(max_length=30, choices=TIPOS, default='otro')


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
    detalle = models.JSONField(default=dict, blank=True)
    ip      = models.GenericIPAddressField(null=True, blank=True)
    fecha   = models.DateTimeField(auto_now_add=True)

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