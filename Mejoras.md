Vas a implementar el sistema completo de comunicación por correo electrónico del sistema. Incluye configuración SMTP desde el panel, plantillas de email por evento y envío automático en todos los flujos críticos.

---

## CONTEXTO

El sistema ya tiene:
- ConfiguracionSistema (singleton con get()) en models.py
- notificar_admins_empresa() y notificar() en notificaciones.py
- registrar_log() en audit.py
- Todos los modelos: Empresa, Usuario, Suscripcion, PagoTransbank, Ruta, SolicitudConductor, Documento, Mantencion

---

## PARTE 1 — CAMPOS NUEVOS EN ConfiguracionSistema (models.py)

Agregar en la clase ConfiguracionSistema existente:

```python
# SMTP
email_host        = models.CharField(max_length=200, blank=True, default='smtp.gmail.com')
email_port        = models.PositiveIntegerField(default=587)
email_host_user   = models.CharField(max_length=200, blank=True, default='')
email_host_password = models.TextField(blank=True, default='')  # cifrado con Fernet
email_use_tls     = models.BooleanField(default=True)
email_use_ssl     = models.BooleanField(default=False)
email_from_name   = models.CharField(max_length=200, blank=True, default='FlotaSystem')
email_from_address = models.EmailField(blank=True, default='')
email_activo      = models.BooleanField(default=False)

# Qué eventos disparan emails (cada uno es un toggle)
notif_pago_aprobado       = models.BooleanField(default=True)
notif_pago_rechazado      = models.BooleanField(default=True)
notif_suscripcion_vence   = models.BooleanField(default=True)
notif_suscripcion_gracia  = models.BooleanField(default=True)
notif_suscripcion_bloqueada = models.BooleanField(default=True)
notif_documento_vence     = models.BooleanField(default=True)
notif_mantencion_vence    = models.BooleanField(default=True)
notif_solicitud_nueva     = models.BooleanField(default=True)
notif_solicitud_resuelta  = models.BooleanField(default=True)
notif_ruta_asignada       = models.BooleanField(default=True)
notif_checklist_fallas    = models.BooleanField(default=True)
notif_bienvenida          = models.BooleanField(default=True)
```

La contraseña SMTP se cifra con Fernet antes de guardar y se descifra al leer.
Agregar métodos:
```python
def set_email_password(self, valor):
    from .models import cifrar
    self.email_host_password = cifrar(valor)

def get_email_password(self):
    from .models import descifrar
    if not self.email_host_password:
        return ''
    try:
        return descifrar(self.email_host_password)
    except Exception:
        return ''
```

---

## PARTE 2 — SERVICIO DE EMAIL (nuevo archivo)

Crear gestion_backend/g_de_flota/email_service.py

### Configuración dinámica del backend SMTP

```python
import logging
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from .models import ConfiguracionSistema

logger = logging.getLogger(__name__)

def get_email_backend():
    """Retorna un backend SMTP configurado con los datos de ConfiguracionSistema."""
    config = ConfiguracionSistema.get()
    if not config.email_activo or not config.email_host_user:
        return None
    return EmailBackend(
        host=config.email_host,
        port=config.email_port,
        username=config.email_host_user,
        password=config.get_email_password(),
        use_tls=config.email_use_tls,
        use_ssl=config.email_use_ssl,
        fail_silently=False,
    )

def enviar_email(destinatario, asunto, html, texto_plano=None, cc=None):
    """
    Envía un email usando la configuración SMTP de ConfiguracionSistema.
    Fail-silent: si falla, loguea el error y retorna False.
    """
    config = ConfiguracionSistema.get()
    if not config.email_activo:
        logger.info(f"Email desactivado — no se envió a {destinatario}")
        return False

    backend = get_email_backend()
    if not backend:
        logger.warning("Email no configurado correctamente.")
        return False

    remitente = f"{config.email_from_name} <{config.email_from_address}>"

    try:
        msg = EmailMultiAlternatives(
            subject=asunto,
            body=texto_plano or _strip_html(html),
            from_email=remitente,
            to=[destinatario] if isinstance(destinatario, str) else destinatario,
            cc=cc or [],
            connection=backend,
        )
        msg.attach_alternative(html, 'text/html')
        msg.send()
        logger.info(f"Email enviado a {destinatario}: {asunto}")
        return True
    except Exception as e:
        logger.error(f"Error al enviar email a {destinatario}: {e}")
        return False

def _strip_html(html):
    """Versión texto plano eliminando tags HTML básicos."""
    import re
    return re.sub(r'<[^>]+>', '', html).strip()
```

### Plantillas de email

Todas las plantillas usan una función base que retorna HTML consistente:

```python
def _base_template(titulo, contenido_html, empresa_nombre='', color_acento='#534AB7'):
    """Plantilla base responsiva para todos los emails."""
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e5e5e5;">
        <tr>
          <td style="background:{color_acento};padding:24px 32px;">
            <p style="margin:0;font-size:20px;font-weight:600;color:#ffffff;">
              {empresa_nombre or 'FlotaSystem'}
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <h1 style="margin:0 0 16px;font-size:22px;color:#1a1a1a;font-weight:600;">{titulo}</h1>
            {contenido_html}
          </td>
        </tr>
        <tr>
          <td style="padding:20px 32px;background:#f9f9f9;border-top:1px solid #e5e5e5;">
            <p style="margin:0;font-size:12px;color:#888888;text-align:center;">
              Este email fue enviado automáticamente por FlotaSystem.<br>
              Por favor no respondas a este correo.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

def _btn(texto, url, color='#534AB7'):
    return f'<a href="{url}" style="display:inline-block;background:{color};color:#ffffff;padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;margin:16px 0;">{texto}</a>'

def _info_row(label, valor):
    return f'<tr><td style="padding:8px 0;color:#666;font-size:14px;width:180px;">{label}</td><td style="padding:8px 0;color:#1a1a1a;font-size:14px;font-weight:600;">{valor}</td></tr>'
```

### Una función por evento — todas con la misma firma: (destinatario_email, **datos)

```python
# ── Bienvenida ────────────────────────────────────────────────────────────────
def email_bienvenida(email, nombre, empresa_nombre, plan_nombre, url_login):
    config = ConfiguracionSistema.get()
    if not config.notif_bienvenida: return
    html = _base_template('Bienvenido a FlotaSystem', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">Tu cuenta en <strong>{empresa_nombre}</strong> ha sido creada exitosamente.</p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;">
            {_info_row('Plan activo:', plan_nombre)}
            {_info_row('Email:', email)}
        </table>
        {_btn('Ingresar al panel', url_login)}
        <p style="color:#888;font-size:13px;">Si no solicitaste esta cuenta, ignora este mensaje.</p>
    """, empresa_nombre)
    enviar_email(email, f'Bienvenido a FlotaSystem — {empresa_nombre}', html)

# ── Pagos ─────────────────────────────────────────────────────────────────────
def email_pago_aprobado(email, nombre, empresa_nombre, plan_nombre, monto, ciclo, fecha_proximo_cobro, orden_compra):
    config = ConfiguracionSistema.get()
    if not config.notif_pago_aprobado: return
    monto_fmt = f'${int(monto):,}'.replace(',', '.')
    html = _base_template('Pago procesado correctamente', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>, tu pago fue procesado exitosamente.</p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
            {_info_row('Orden de compra:', orden_compra)}
            {_info_row('Plan:', plan_nombre)}
            {_info_row('Ciclo:', ciclo.capitalize())}
            {_info_row('Monto pagado:', monto_fmt + ' CLP')}
            {_info_row('Próximo cobro:', fecha_proximo_cobro)}
        </table>
        <div style="background:#E1F5EE;border-radius:8px;padding:16px;margin:16px 0;">
            <p style="margin:0;color:#085041;font-size:14px;">✓ Tu plan está activo y todos los módulos están disponibles.</p>
        </div>
    """, empresa_nombre)
    enviar_email(email, f'Pago aprobado — {monto_fmt} CLP', html)

def email_pago_rechazado(email, nombre, empresa_nombre, monto, url_reintentar):
    config = ConfiguracionSistema.get()
    if not config.notif_pago_rechazado: return
    monto_fmt = f'${int(monto):,}'.replace(',', '.')
    html = _base_template('Tu pago no pudo ser procesado', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">Lamentablemente tu pago de <strong>{monto_fmt} CLP</strong> fue rechazado por Transbank.</p>
        <p style="color:#444;font-size:14px;">Posibles causas: fondos insuficientes, tarjeta bloqueada o datos incorrectos.</p>
        {_btn('Reintentar pago', url_reintentar, '#E24B4A')}
        <p style="color:#888;font-size:13px;">Si el problema persiste, contacta a tu banco.</p>
    """, empresa_nombre)
    enviar_email(email, 'Pago rechazado — acción requerida', html)

# ── Suscripción ───────────────────────────────────────────────────────────────
def email_suscripcion_vence(email, nombre, empresa_nombre, plan_nombre, dias, fecha_vencimiento, url_pago):
    config = ConfiguracionSistema.get()
    if not config.notif_suscripcion_vence: return
    html = _base_template(f'Tu suscripción vence en {dias} días', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">Tu plan <strong>{plan_nombre}</strong> vence el <strong>{fecha_vencimiento}</strong>.</p>
        <div style="background:#FAEEDA;border-radius:8px;padding:16px;margin:16px 0;">
            <p style="margin:0;color:#633806;font-size:14px;">⚠ Renueva antes de esa fecha para evitar interrupciones en el servicio.</p>
        </div>
        {_btn('Renovar ahora', url_pago, '#BA7517')}
    """, empresa_nombre)
    enviar_email(email, f'Tu suscripción vence en {dias} días', html)

def email_suscripcion_gracia(email, nombre, empresa_nombre, dias_gracia_restantes, url_pago):
    config = ConfiguracionSistema.get()
    if not config.notif_suscripcion_gracia: return
    html = _base_template('Período de gracia — pago pendiente', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">Tu suscripción ha vencido. Tienes <strong>{dias_gracia_restantes} días</strong> para regularizar el pago.</p>
        <div style="background:#FCEBEB;border-radius:8px;padding:16px;margin:16px 0;">
            <p style="margin:0;color:#791F1F;font-size:14px;">Si no pagas antes de que termine el período de gracia, el servicio será suspendido automáticamente.</p>
        </div>
        {_btn('Pagar ahora', url_pago, '#E24B4A')}
    """, empresa_nombre)
    enviar_email(email, 'Acción requerida — pago pendiente', html)

def email_suscripcion_bloqueada(email, nombre, empresa_nombre, url_pago):
    config = ConfiguracionSistema.get()
    if not config.notif_suscripcion_bloqueada: return
    html = _base_template('Servicio suspendido', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">El acceso a <strong>{empresa_nombre}</strong> ha sido suspendido por falta de pago.</p>
        <p style="color:#444;font-size:14px;">Para reactivar el servicio, regulariza el pago a través del siguiente enlace:</p>
        {_btn('Reactivar servicio', url_pago, '#E24B4A')}
    """, empresa_nombre)
    enviar_email(email, 'Servicio suspendido — acción requerida', html)

# ── Documentos ────────────────────────────────────────────────────────────────
def email_documento_vence(email, nombre, empresa_nombre, tipo_documento, entidad_nombre, dias, fecha_vencimiento, url_documentos):
    config = ConfiguracionSistema.get()
    if not config.notif_documento_vence: return
    nivel = 'vencido' if dias < 0 else 'por vencer'
    titulo = f'Documento {nivel}: {tipo_documento}'
    html = _base_template(titulo, f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
            {_info_row('Documento:', tipo_documento)}
            {_info_row('Asociado a:', entidad_nombre)}
            {_info_row('Vencimiento:', fecha_vencimiento)}
            {_info_row('Estado:', f'Vencido hace {abs(dias)} días' if dias < 0 else f'Vence en {dias} días')}
        </table>
        {_btn('Gestionar documentos', url_documentos)}
    """, empresa_nombre)
    enviar_email(email, titulo, html)

# ── Mantención ────────────────────────────────────────────────────────────────
def email_mantencion_vence(email, nombre, empresa_nombre, tipo_mantencion, patente, dias, url_mantenciones):
    config = ConfiguracionSistema.get()
    if not config.notif_mantencion_vence: return
    html = _base_template(f'Mantención pendiente: {tipo_mantencion}', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">El vehículo <strong>{patente}</strong> tiene una mantención pendiente.</p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
            {_info_row('Tipo:', tipo_mantencion)}
            {_info_row('Vehículo:', patente)}
            {_info_row('Días restantes:', str(dias) if dias >= 0 else f'{abs(dias)} días vencida')}
        </table>
        {_btn('Ver mantenciones', url_mantenciones)}
    """, empresa_nombre)
    enviar_email(email, f'Mantención pendiente — {patente}', html)

# ── Solicitudes ───────────────────────────────────────────────────────────────
def email_solicitud_nueva(email, nombre_admin, empresa_nombre, tipo, titulo_sol, conductor_nombre, url_solicitudes):
    config = ConfiguracionSistema.get()
    if not config.notif_solicitud_nueva: return
    html = _base_template(f'Nueva solicitud de conductor', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre_admin}</strong>,</p>
        <p style="color:#444;font-size:15px;"><strong>{conductor_nombre}</strong> envió una nueva solicitud.</p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
            {_info_row('Tipo:', tipo.capitalize())}
            {_info_row('Descripción:', titulo_sol)}
            {_info_row('Conductor:', conductor_nombre)}
        </table>
        {_btn('Ver solicitud', url_solicitudes)}
    """, empresa_nombre)
    enviar_email(email, f'Nueva solicitud: {titulo_sol}', html)

def email_solicitud_resuelta(email, nombre_conductor, empresa_nombre, titulo_sol, estado, respuesta, url_app):
    config = ConfiguracionSistema.get()
    if not config.notif_solicitud_resuelta: return
    color  = '#1D9E75' if estado == 'aprobado' else '#E24B4A'
    icono  = '✓' if estado == 'aprobado' else '✗'
    html = _base_template(f'Solicitud {estado}', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre_conductor}</strong>,</p>
        <p style="color:#444;font-size:15px;">Tu solicitud <strong>"{titulo_sol}"</strong> fue <strong style="color:{color};">{estado}</strong>.</p>
        {'<div style="background:#f5f5f5;border-radius:8px;padding:16px;margin:16px 0;"><p style="margin:0;color:#444;font-size:14px;"><strong>Respuesta del administrador:</strong><br>' + respuesta + '</p></div>' if respuesta else ''}
        {_btn('Ver en la app', url_app)}
    """, empresa_nombre)
    enviar_email(email, f'Solicitud {estado}: {titulo_sol}', html)

# ── Ruta ─────────────────────────────────────────────────────────────────────
def email_ruta_asignada(email, nombre_conductor, empresa_nombre, nombre_ruta, origen, destino, fecha, url_app):
    config = ConfiguracionSistema.get()
    if not config.notif_ruta_asignada: return
    html = _base_template(f'Nueva ruta asignada: {nombre_ruta}', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre_conductor}</strong>,</p>
        <p style="color:#444;font-size:15px;">Se te asignó una nueva ruta.</p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
            {_info_row('Ruta:', nombre_ruta)}
            {_info_row('Origen:', origen)}
            {_info_row('Destino:', destino)}
            {_info_row('Fecha:', fecha)}
        </table>
        {_btn('Ver en la app', url_app)}
    """, empresa_nombre)
    enviar_email(email, f'Nueva ruta asignada: {nombre_ruta}', html)

def email_checklist_fallas(email, nombre_admin, empresa_nombre, conductor_nombre, patente, fallas, url_solicitudes):
    config = ConfiguracionSistema.get()
    if not config.notif_checklist_fallas: return
    fallas_html = ''.join(f'<li style="color:#791F1F;font-size:14px;margin-bottom:4px;">{f}</li>' for f in fallas)
    html = _base_template('Checklist pre-viaje con fallas', f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre_admin}</strong>,</p>
        <p style="color:#444;font-size:15px;"><strong>{conductor_nombre}</strong> detectó fallas en el vehículo <strong>{patente}</strong> antes de partir.</p>
        <div style="background:#FCEBEB;border-radius:8px;padding:16px;margin:16px 0;">
            <p style="margin:0 0 8px;color:#791F1F;font-size:14px;font-weight:600;">Fallas detectadas:</p>
            <ul style="margin:0;padding-left:20px;">{fallas_html}</ul>
        </div>
        {_btn('Ver solicitud', url_solicitudes)}
    """, empresa_nombre)
    enviar_email(email, f'⚠ Fallas en checklist — {patente}', html)
```

---

## PARTE 3 — INTEGRAR EMAILS EN LOS FLUJOS EXISTENTES

En cada archivo indicado, agregar el import y llamar a la función correspondiente.
Todas las llamadas a email_* son fire-and-forget — no bloquean la respuesta.

### views_planes.py — PagoRetornoView
Después de `sus.save()` en pago aprobado:
```python
from .email_service import email_pago_aprobado
try:
    admins = Usuario.objects.filter(empresa=pago.empresa, rol='USUARIO', is_active=True)
    for admin in admins:
        email_pago_aprobado(
            email=admin.email,
            nombre=descifrar(admin.nombre_cifrado),
            empresa_nombre=pago.empresa.nombre,
            plan_nombre=pago.plan_nombre,
            monto=pago.monto,
            ciclo=pago.ciclo,
            fecha_proximo_cobro=sus.fecha_fin_periodo.strftime('%d/%m/%Y'),
            orden_compra=pago.orden_compra,
        )
except Exception: pass
```

Después de `pago.estado = 'rechazado'`:
```python
from .email_service import email_pago_rechazado
try:
    for admin in admins:
        email_pago_rechazado(
            email=admin.email,
            nombre=descifrar(admin.nombre_cifrado),
            empresa_nombre=pago.empresa.nombre,
            monto=pago.monto,
            url_reintentar=f"{settings.FRONTEND_URL}/empresa/pago",
        )
except Exception: pass
```

### management/commands/verificar_suscripciones.py
En cada bloque de notificación, agregar el email correspondiente:
- Al pasar a gracia: email_suscripcion_gracia()
- Al suspender: email_suscripcion_bloqueada()
- Al avisar vencimiento próximo: email_suscripcion_vence()

### management/commands/verificar_documentos.py
En cada notificación de documento vencido o por vencer:
```python
from .email_service import email_documento_vence
try:
    admins = Usuario.objects.filter(empresa=doc.empresa, rol='USUARIO', is_active=True)
    for admin in admins:
        email_documento_vence(
            email=admin.email,
            nombre=descifrar(admin.nombre_cifrado),
            empresa_nombre=doc.empresa.nombre,
            tipo_documento=doc.get_tipo_display(),
            entidad_nombre=doc.vehiculo.patente if doc.vehiculo else descifrar(doc.conductor.nombre_cifrado),
            dias=dias,
            fecha_vencimiento=doc.fecha_vencimiento.strftime('%d/%m/%Y'),
            url_documentos=f"{settings.FRONTEND_URL}/empresa/documentos",
        )
except Exception: pass
```

### views.py — crear usuario
Al crear un usuario nuevo con rol USUARIO:
```python
from .email_service import email_bienvenida
try:
    email_bienvenida(
        email=nuevo_usuario.email,
        nombre=descifrar(nuevo_usuario.nombre_cifrado),
        empresa_nombre=nuevo_usuario.empresa.nombre if nuevo_usuario.empresa else '',
        plan_nombre=nuevo_usuario.empresa.plan.get_nombre_display() if nuevo_usuario.empresa and nuevo_usuario.empresa.plan else 'Sin plan',
        url_login=f"{settings.FRONTEND_URL}/login",
    )
except Exception: pass
```

### views.py — crear ruta
Al crear una ruta y asignar conductor:
```python
from .email_service import email_ruta_asignada
if ruta.conductor:
    try:
        email_ruta_asignada(
            email=ruta.conductor.email,
            nombre_conductor=descifrar(ruta.conductor.nombre_cifrado),
            empresa_nombre=ruta.empresa.nombre,
            nombre_ruta=ruta.nombre,
            origen=ruta.paradas.filter(tipo='origen').first().nombre if ruta.paradas.exists() else '—',
            destino=ruta.paradas.filter(tipo='destino').first().nombre if ruta.paradas.exists() else '—',
            fecha=ruta.fecha_programada.strftime('%d/%m/%Y %H:%M') if ruta.fecha_programada else '—',
            url_app=f"{settings.FRONTEND_URL}/app",
        )
    except Exception: pass
```

### views.py — aprobar/rechazar solicitud
Al aprobar:
```python
from .email_service import email_solicitud_resuelta
try:
    email_solicitud_resuelta(
        email=sol.conductor.email,
        nombre_conductor=descifrar(sol.conductor.nombre_cifrado),
        empresa_nombre=sol.empresa.nombre,
        titulo_sol=sol.titulo,
        estado='aprobado',
        respuesta=sol.respuesta,
        url_app=f"{settings.FRONTEND_URL}/app",
    )
except Exception: pass
```

### views.py — nueva solicitud de conductor
Al crear solicitud:
```python
from .email_service import email_solicitud_nueva
try:
    admins = Usuario.objects.filter(empresa=sol.empresa, rol='USUARIO', is_active=True)
    for admin in admins:
        email_solicitud_nueva(
            email=admin.email,
            nombre_admin=descifrar(admin.nombre_cifrado),
            empresa_nombre=sol.empresa.nombre,
            tipo=sol.tipo,
            titulo_sol=sol.titulo,
            conductor_nombre=descifrar(sol.conductor.nombre_cifrado),
            url_solicitudes=f"{settings.FRONTEND_URL}/empresa/solicitudes",
        )
except Exception: pass
```

### views.py — checklist con fallas
En ChecklistView POST cuando tiene_fallas:
```python
from .email_service import email_checklist_fallas
try:
    admins = Usuario.objects.filter(empresa=ruta.empresa, rol='USUARIO', is_active=True)
    for admin in admins:
        email_checklist_fallas(
            email=admin.email,
            nombre_admin=descifrar(admin.nombre_cifrado),
            empresa_nombre=ruta.empresa.nombre,
            conductor_nombre=descifrar(request.user.nombre_cifrado),
            patente=ruta.vehiculo.patente if ruta.vehiculo else '—',
            fallas=resumen_fallas,
            url_solicitudes=f"{settings.FRONTEND_URL}/empresa/solicitudes",
        )
except Exception: pass
```

---

## PARTE 4 — ENDPOINT DE CONFIGURACIÓN EMAIL (views_planes.py)

### GET/PUT /api/admin/email/
Solo SUPERADMIN.

GET retorna la configuración con la contraseña enmascarada:
```json
{
  "email_host": "smtp.gmail.com",
  "email_port": 587,
  "email_host_user": "notif@empresa.cl",
  "email_host_password": "••••••••",
  "email_use_tls": true,
  "email_use_ssl": false,
  "email_from_name": "FlotaSystem",
  "email_from_address": "notif@empresa.cl",
  "email_activo": true,
  "notificaciones": {
    "pago_aprobado": true,
    "pago_rechazado": true,
    "suscripcion_vence": true,
    ...
  }
}
```

PUT actualiza los campos. Si email_host_password viene como "••••••••" ignorarlo (no actualizar).

### POST /api/admin/email/test/
Solo SUPERADMIN.
Body: { email_destino }
Envía un email de prueba al destinatario indicado usando la configuración actual.
Si falla retorna el error específico de SMTP para que el admin pueda diagnosticar.

```python
class EmailTestView(View):
    def post(self, request):
        if request.user.rol != 'SUPERADMIN':
            return JsonResponse({'error': 'Sin acceso.'}, status=403)
        body    = json.loads(request.body)
        destino = body.get('email_destino')
        if not destino:
            return JsonResponse({'error': 'Email destino requerido.'}, status=400)
        config = ConfiguracionSistema.get()
        from .email_service import _base_template, enviar_email
        html = _base_template('Email de prueba', f"""
            <p style="color:#444;font-size:15px;">Este es un email de prueba enviado desde FlotaSystem.</p>
            <p style="color:#888;font-size:13px;">Si recibes este mensaje, la configuración SMTP es correcta.</p>
            <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
                <tr><td style="color:#666;font-size:13px;padding:4px 0;">Servidor SMTP:</td><td style="color:#1a1a1a;font-size:13px;">{config.email_host}:{config.email_port}</td></tr>
                <tr><td style="color:#666;font-size:13px;padding:4px 0;">Usuario:</td><td style="color:#1a1a1a;font-size:13px;">{config.email_host_user}</td></tr>
            </table>
        """)
        try:
            from .email_service import get_email_backend, EmailMultiAlternatives
            backend  = get_email_backend()
            remitente = f"{config.email_from_name} <{config.email_from_address}>"
            msg = EmailMultiAlternatives(
                subject='Email de prueba — FlotaSystem',
                body='Email de prueba desde FlotaSystem.',
                from_email=remitente,
                to=[destino],
                connection=backend,
            )
            msg.attach_alternative(html, 'text/html')
            msg.send()
            return JsonResponse({'ok': True, 'mensaje': f'Email de prueba enviado a {destino}'})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)
```

---

## PARTE 5 — URLS (agregar en urls.py)

```python
path('api/admin/email/',       EmailConfigView.as_view()),
path('api/admin/email/test/',  EmailTestView.as_view()),
```

---

## PARTE 6 — VARIABLE FRONTEND_URL EN SETTINGS

Agregar en settings.py:
```python
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:7183')
```

Agregar en .env:
FRONTEND_URL=http://localhost:7183

---

## PARTE 7 — FRONTEND: módulo de configuración de email

### Agregar tab "Email" en la vista de Configuracion.vue del SUPERADMIN

El tab tiene dos secciones:

#### Sección 1 — Configuración SMTP
Campos:
- Servidor SMTP (input text, default smtp.gmail.com)
- Puerto (input number, default 587)
- Usuario (input email)
- Contraseña (input password con toggle mostrar/ocultar)
- Nombre del remitente (input text, ej: "FlotaSystem")
- Email del remitente (input email)
- Toggle TLS / Toggle SSL (mutuamente excluyentes)
- Toggle "Envío de emails activado"

Botones: "Guardar configuración" y "Enviar email de prueba"

Al "Enviar email de prueba": modal pequeño que pide el email destino, luego POST /api/admin/email/test/ y muestra resultado.

Guías rápidas de configuración (texto colapsable):
- Gmail: smtp.gmail.com · puerto 587 · TLS activado · requiere "contraseña de aplicación" (no la contraseña normal)
- Outlook: smtp.office365.com · puerto 587 · TLS activado
- IONOS/1&1: smtp.ionos.es · puerto 587 · TLS activado

#### Sección 2 — Notificaciones por evento
Tabla con toggle por cada evento:
Evento                          | Email activo
──────────────────────────────────────────────
Bienvenida a nuevo usuario      | [toggle]
Pago aprobado                   | [toggle]
Pago rechazado                  | [toggle]
Suscripción por vencer          | [toggle]
Período de gracia               | [toggle]
Servicio suspendido             | [toggle]
Documento por vencer / vencido  | [toggle]
Mantención pendiente            | [toggle]
Nueva solicitud de conductor    | [toggle]
Solicitud aprobada/rechazada    | [toggle]
Ruta asignada a conductor       | [toggle]
Checklist con fallas            | [toggle]

Botón "Guardar notificaciones" al pie.

---

## CONVENCIONES
- Todas las llamadas a email_* envueltas en try/except — nunca romper el flujo principal
- Contraseña SMTP cifrada con Fernet en DB, nunca en texto plano
- La contraseña nunca se retorna completa en el GET — siempre "••••••••"
- Solo actualizar la contraseña en el PUT si el valor enviado no es "••••••••"
- registrar_log en: guardar config email, enviar test
- Los emails no bloquean la respuesta HTTP — si fallan, solo loguear
- Textos en español es-CL en todos los templates
- FRONTEND_URL se lee de settings en todos los links de los emails
- Sin "# resto igual"

---

## ARCHIVOS A ENTREGAR

Backend:
1. models_patch.py — campos nuevos en ConfiguracionSistema
2. email_service.py — completo
3. views_email_patch.py — EmailConfigView y EmailTestView con indicación de dónde van en views_planes.py
4. integraciones_patch.py — fragmentos exactos a agregar en cada vista existente (con indicación de archivo y función)
5. urls_patch.py — las 2 rutas nuevas
6. settings_patch.py — FRONTEND_URL a agregar

Frontend:
7. configuracion_email_tab.vue — el tab completo de email para agregar en Configuracion.vue con indicación de dónde insertar

Sin "# resto igual".