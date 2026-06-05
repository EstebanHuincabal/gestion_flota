"""
email_service.py — Servicio centralizado de envío de emails para FlotaSystem.

- Usa la configuración SMTP almacenada en ConfiguracionSistema (dinámica, sin .env).
- Todas las funciones email_* son fire-and-forget: no lanzan excepciones.
- La contraseña SMTP está cifrada con Fernet en la BD.
- Cada función verifica su toggle individual antes de enviar.
"""
import logging
import re

from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Backend SMTP dinámico
# ─────────────────────────────────────────────────────────────────────────────

def get_email_backend():
    """Retorna un EmailBackend configurado con los datos de ConfiguracionSistema."""
    from .models import ConfiguracionSistema
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
    Envía un email con la configuración SMTP de ConfiguracionSistema.
    Fail-silent: si falla, loguea el error y retorna False.
    """
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.email_activo:
        logger.info(f"[EMAIL] Desactivado — no se envió a {destinatario}")
        return False

    backend = get_email_backend()
    if not backend:
        logger.warning("[EMAIL] No configurado correctamente.")
        return False

    remitente = f"{config.email_from_name} <{config.email_from_address}>"
    destinos  = [destinatario] if isinstance(destinatario, str) else destinatario

    try:
        msg = EmailMultiAlternatives(
            subject=asunto,
            body=texto_plano or _strip_html(html),
            from_email=remitente,
            to=destinos,
            cc=cc or [],
            connection=backend,
        )
        msg.attach_alternative(html, 'text/html')
        msg.send()
        logger.info(f"[EMAIL] Enviado a {destinatario}: {asunto}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL] Error al enviar a {destinatario}: {e}")
        return False


def _strip_html(html):
    """Versión texto plano eliminando tags HTML."""
    return re.sub(r'<[^>]+>', '', html).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Plantilla base responsiva
# ─────────────────────────────────────────────────────────────────────────────

def _base_template(titulo, contenido_html, empresa_nombre='', color_acento='#534AB7'):
    """Plantilla HTML base para todos los emails del sistema."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e5e5e5;">
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
              Este correo fue enviado automáticamente por FlotaSystem.<br>
              Por favor no respondas a este mensaje.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _btn(texto, url, color='#534AB7'):
    return (
        f'<a href="{url}" style="display:inline-block;background:{color};color:#ffffff;'
        f'padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px;'
        f'font-weight:600;margin:16px 0;">{texto}</a>'
    )


def _info_row(label, valor):
    return (
        f'<tr>'
        f'<td style="padding:8px 0;color:#666;font-size:14px;width:180px;">{label}</td>'
        f'<td style="padding:8px 0;color:#1a1a1a;font-size:14px;font-weight:600;">{valor}</td>'
        f'</tr>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Funciones de email por evento
# ─────────────────────────────────────────────────────────────────────────────

def email_bienvenida(email, nombre, empresa_nombre, plan_nombre, url_login):
    """Email de bienvenida al crear un usuario nuevo."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_bienvenida:
        return
    html = _base_template(
        'Bienvenido a FlotaSystem',
        f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">
          Tu cuenta en <strong>{empresa_nombre}</strong> ha sido creada exitosamente.
        </p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;">
          {_info_row('Plan activo:', plan_nombre)}
          {_info_row('Email:', email)}
        </table>
        {_btn('Ingresar al panel', url_login)}
        <p style="color:#888;font-size:13px;">
          Si no solicitaste esta cuenta, puedes ignorar este mensaje.
        </p>
        """,
        empresa_nombre,
    )
    enviar_email(email, f'Bienvenido a FlotaSystem — {empresa_nombre}', html)


# ── Pagos ─────────────────────────────────────────────────────────────────────

def email_pago_aprobado(email, nombre, empresa_nombre, plan_nombre, monto, ciclo,
                         fecha_proximo_cobro, orden_compra):
    """Confirmación de pago aprobado."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_pago_aprobado:
        return
    monto_fmt = f'${int(monto):,}'.replace(',', '.')
    html = _base_template(
        'Pago procesado correctamente',
        f"""
        <p style="color:#444;font-size:15px;">
          Hola <strong>{nombre}</strong>, tu pago fue procesado exitosamente.
        </p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
          {_info_row('Orden de compra:', orden_compra)}
          {_info_row('Plan:', plan_nombre)}
          {_info_row('Ciclo:', ciclo.capitalize())}
          {_info_row('Monto pagado:', monto_fmt + ' CLP')}
          {_info_row('Próximo cobro:', fecha_proximo_cobro)}
        </table>
        <div style="background:#E1F5EE;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:0;color:#085041;font-size:14px;">
            ✓ Tu plan está activo y todos los módulos están disponibles.
          </p>
        </div>
        """,
        empresa_nombre,
    )
    enviar_email(email, f'Pago aprobado — {monto_fmt} CLP', html)


def email_pago_rechazado(email, nombre, empresa_nombre, monto, url_reintentar):
    """Aviso de pago rechazado."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_pago_rechazado:
        return
    monto_fmt = f'${int(monto):,}'.replace(',', '.')
    html = _base_template(
        'Tu pago no pudo ser procesado',
        f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">
          Lamentablemente tu pago de <strong>{monto_fmt} CLP</strong>
          fue rechazado por Transbank.
        </p>
        <p style="color:#444;font-size:14px;">
          Posibles causas: fondos insuficientes, tarjeta bloqueada o datos incorrectos.
        </p>
        {_btn('Reintentar pago', url_reintentar, '#E24B4A')}
        <p style="color:#888;font-size:13px;">
          Si el problema persiste, contacta a tu banco o al administrador del sistema.
        </p>
        """,
        empresa_nombre,
    )
    enviar_email(email, 'Pago rechazado — acción requerida', html)


# ── Suscripción ───────────────────────────────────────────────────────────────

def email_suscripcion_vence(email, nombre, empresa_nombre, plan_nombre, dias,
                             fecha_vencimiento, url_pago):
    """Aviso de suscripción próxima a vencer."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_suscripcion_vence:
        return
    html = _base_template(
        f'Tu suscripción vence en {dias} días',
        f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">
          Tu plan <strong>{plan_nombre}</strong> vence el <strong>{fecha_vencimiento}</strong>.
        </p>
        <div style="background:#FAEEDA;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:0;color:#633806;font-size:14px;">
            ⚠ Renueva antes de esa fecha para evitar interrupciones en el servicio.
          </p>
        </div>
        {_btn('Renovar ahora', url_pago, '#BA7517')}
        """,
        empresa_nombre,
    )
    enviar_email(email, f'Tu suscripción vence en {dias} días', html)


def email_suscripcion_gracia(email, nombre, empresa_nombre, dias_gracia_restantes, url_pago):
    """Aviso de período de gracia iniciado."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_suscripcion_gracia:
        return
    html = _base_template(
        'Período de gracia — pago pendiente',
        f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">
          Tu suscripción ha vencido. Tienes
          <strong>{dias_gracia_restantes} días</strong> para regularizar el pago.
        </p>
        <div style="background:#FCEBEB;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:0;color:#791F1F;font-size:14px;">
            Si no pagas antes de que termine el período de gracia, el servicio
            será suspendido automáticamente.
          </p>
        </div>
        {_btn('Pagar ahora', url_pago, '#E24B4A')}
        """,
        empresa_nombre,
    )
    enviar_email(email, 'Acción requerida — pago pendiente', html)


def email_suscripcion_bloqueada(email, nombre, empresa_nombre, url_pago):
    """Aviso de servicio suspendido por falta de pago."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_suscripcion_bloqueada:
        return
    html = _base_template(
        'Servicio suspendido',
        f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">
          El acceso a <strong>{empresa_nombre}</strong> ha sido suspendido
          por falta de pago.
        </p>
        <p style="color:#444;font-size:14px;">
          Para reactivar el servicio, regulariza el pago a través del
          siguiente enlace:
        </p>
        {_btn('Reactivar servicio', url_pago, '#E24B4A')}
        """,
        empresa_nombre,
    )
    enviar_email(email, 'Servicio suspendido — acción requerida', html)


# ── Documentos ────────────────────────────────────────────────────────────────

def email_documento_vence(email, nombre, empresa_nombre, tipo_documento, entidad_nombre,
                           dias, fecha_vencimiento, url_documentos):
    """Aviso de documento vencido o por vencer."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_documento_vence:
        return
    nivel  = 'vencido' if dias < 0 else 'por vencer'
    titulo = f'Documento {nivel}: {tipo_documento}'
    html   = _base_template(
        titulo,
        f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
          {_info_row('Documento:', tipo_documento)}
          {_info_row('Asociado a:', entidad_nombre)}
          {_info_row('Vencimiento:', fecha_vencimiento)}
          {_info_row('Estado:', f'Vencido hace {abs(dias)} días' if dias < 0 else f'Vence en {dias} días')}
        </table>
        {_btn('Gestionar documentos', url_documentos)}
        """,
        empresa_nombre,
    )
    enviar_email(email, titulo, html)


# ── Mantención ────────────────────────────────────────────────────────────────

def email_mantencion_vence(email, nombre, empresa_nombre, tipo_mantencion, patente,
                            dias, url_mantenciones):
    """Aviso de mantención pendiente o próxima a vencer."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_mantencion_vence:
        return
    html = _base_template(
        f'Mantención pendiente: {tipo_mantencion}',
        f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">
          El vehículo <strong>{patente}</strong> tiene una mantención pendiente.
        </p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
          {_info_row('Tipo:', tipo_mantencion)}
          {_info_row('Vehículo:', patente)}
          {_info_row('Días restantes:',
                     str(dias) if dias >= 0 else f'{abs(dias)} días vencida')}
        </table>
        {_btn('Ver mantenciones', url_mantenciones)}
        """,
        empresa_nombre,
    )
    enviar_email(email, f'Mantención pendiente — {patente}', html)


# ── Solicitudes ───────────────────────────────────────────────────────────────

def email_solicitud_nueva(email, nombre_admin, empresa_nombre, tipo, titulo_sol,
                           conductor_nombre, url_solicitudes):
    """Aviso de nueva solicitud de conductor (notifica a los admins)."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_solicitud_nueva:
        return
    html = _base_template(
        'Nueva solicitud de conductor',
        f"""
        <p style="color:#444;font-size:15px;">
          Hola <strong>{nombre_admin}</strong>,
        </p>
        <p style="color:#444;font-size:15px;">
          <strong>{conductor_nombre}</strong> envió una nueva solicitud.
        </p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
          {_info_row('Tipo:', tipo.capitalize())}
          {_info_row('Descripción:', titulo_sol)}
          {_info_row('Conductor:', conductor_nombre)}
        </table>
        {_btn('Ver solicitud', url_solicitudes)}
        """,
        empresa_nombre,
    )
    enviar_email(email, f'Nueva solicitud: {titulo_sol}', html)


def email_solicitud_resuelta(email, nombre_conductor, empresa_nombre, titulo_sol,
                              estado, respuesta, url_app):
    """Aviso al conductor de que su solicitud fue aprobada o rechazada."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_solicitud_resuelta:
        return
    color = '#1D9E75' if estado == 'aprobado' else '#E24B4A'
    respuesta_bloque = (
        f'<div style="background:#f5f5f5;border-radius:8px;padding:16px;margin:16px 0;">'
        f'<p style="margin:0;color:#444;font-size:14px;">'
        f'<strong>Respuesta del administrador:</strong><br>{respuesta}'
        f'</p></div>'
        if respuesta else ''
    )
    html = _base_template(
        f'Solicitud {estado}',
        f"""
        <p style="color:#444;font-size:15px;">
          Hola <strong>{nombre_conductor}</strong>,
        </p>
        <p style="color:#444;font-size:15px;">
          Tu solicitud <strong>"{titulo_sol}"</strong> fue
          <strong style="color:{color};">{estado}</strong>.
        </p>
        {respuesta_bloque}
        {_btn('Ver en la app', url_app)}
        """,
        empresa_nombre,
    )
    enviar_email(email, f'Solicitud {estado}: {titulo_sol}', html)


# ── Ruta ─────────────────────────────────────────────────────────────────────

def email_ruta_asignada(email, nombre_conductor, empresa_nombre, nombre_ruta,
                         origen, destino, fecha, url_app):
    """Aviso al conductor de nueva ruta asignada."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_ruta_asignada:
        return
    html = _base_template(
        f'Nueva ruta asignada: {nombre_ruta}',
        f"""
        <p style="color:#444;font-size:15px;">
          Hola <strong>{nombre_conductor}</strong>,
        </p>
        <p style="color:#444;font-size:15px;">
          Se te asignó una nueva ruta.
        </p>
        <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
          {_info_row('Ruta:', nombre_ruta)}
          {_info_row('Origen:', origen)}
          {_info_row('Destino:', destino)}
          {_info_row('Fecha:', fecha)}
        </table>
        {_btn('Ver en la app', url_app)}
        """,
        empresa_nombre,
    )
    enviar_email(email, f'Nueva ruta asignada: {nombre_ruta}', html)


# ── Checklist con fallas ──────────────────────────────────────────────────────

def email_checklist_fallas(email, nombre_admin, empresa_nombre, conductor_nombre,
                            patente, fallas, url_solicitudes):
    """Aviso a los admins cuando un checklist pre-viaje detecta fallas."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_checklist_fallas:
        return
    fallas_html = ''.join(
        f'<li style="color:#791F1F;font-size:14px;margin-bottom:4px;">{f}</li>'
        for f in (fallas if isinstance(fallas, list) else [fallas])
    )
    html = _base_template(
        'Checklist pre-viaje con fallas',
        f"""
        <p style="color:#444;font-size:15px;">
          Hola <strong>{nombre_admin}</strong>,
        </p>
        <p style="color:#444;font-size:15px;">
          <strong>{conductor_nombre}</strong> detectó fallas en el vehículo
          <strong>{patente}</strong> antes de partir.
        </p>
        <div style="background:#FCEBEB;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:0 0 8px;color:#791F1F;font-size:14px;font-weight:600;">
            Fallas detectadas:
          </p>
          <ul style="margin:0;padding-left:20px;">{fallas_html}</ul>
        </div>
        {_btn('Ver solicitud', url_solicitudes)}
        """,
        empresa_nombre,
    )
    enviar_email(email, f'⚠ Fallas en checklist — {patente}', html)


def email_checklist_ok(email, nombre_admin, empresa_nombre, conductor_nombre,
                       patente, ruta_nombre, url_solicitudes):
    """Aviso a los admins cuando un checklist pre-viaje se completa SIN fallas."""
    html = _base_template(
        'Checklist pre-viaje completado',
        f"""
        <p style="color:#444;font-size:15px;">
          Hola <strong>{nombre_admin}</strong>,
        </p>
        <p style="color:#444;font-size:15px;">
          <strong>{conductor_nombre}</strong> completó el checklist del vehículo
          <strong>{patente}</strong> para la ruta <strong>{ruta_nombre}</strong>.
        </p>
        <div style="background:#ECFDF5;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:0;color:#065F46;font-size:14px;font-weight:600;">
            ✓ Vehículo en orden — listo para partir.
          </p>
        </div>
        {_btn('Ver checklist', url_solicitudes)}
        """,
        empresa_nombre,
    )
    enviar_email(email, f'✓ Checklist en orden — {patente}', html)


# ── Aviso interno (módulo de Avisos) ─────────────────────────────────────────

def email_aviso(email, nombre_destinatario, empresa_nombre, nombre_emisor, asunto, mensaje):
    """Aviso interno enviado desde el módulo de Avisos (admin → flota/conductor, conductor → admins)."""
    html = _base_template(
        asunto,
        f"""
        <p style="color:#444;font-size:15px;">
          Hola <strong>{nombre_destinatario}</strong>,
        </p>
        <p style="color:#444;font-size:15px;">
          Tienes un nuevo aviso de <strong>{nombre_emisor}</strong>:
        </p>
        <div style="background:#EFF6FF;border-left:4px solid #3B82F6;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:0 0 8px 0;color:#1E40AF;font-size:14px;font-weight:600;">{asunto}</p>
          <p style="margin:0;color:#374151;font-size:14px;white-space:pre-wrap;">{mensaje}</p>
        </div>
        """,
        empresa_nombre,
    )
    enviar_email(email, f'📢 {asunto}', html)


# ── Acceso inicial conductor (creado sin contraseña) ─────────────────────────

def email_acceso_conductor(email, nombre, empresa_nombre, rut, clave_temporal):
    """
    Enviado al conductor recién creado cuando no se le asignó contraseña manual.
    Le entrega sus credenciales de acceso a la app móvil.
    """
    html = _base_template(
        f'Bienvenido/a a {empresa_nombre}',
        f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">
          Tu cuenta de conductor fue creada en <strong>{empresa_nombre}</strong>.
          Estos son tus datos de acceso para la app móvil:
        </p>
        <div style="background:#F0F4FF;border-radius:8px;padding:20px;margin:16px 0;">
          <table cellpadding="0" cellspacing="0" style="width:100%;">
            <tr>
              <td style="color:#666;font-size:13px;padding:4px 0;width:110px;">RUT:</td>
              <td style="color:#222;font-size:14px;font-weight:600;">{rut}</td>
            </tr>
            <tr>
              <td style="color:#666;font-size:13px;padding:4px 0;">Contraseña:</td>
              <td>
                <span style="font-family:monospace,Courier New,monospace;font-size:20px;font-weight:700;color:#534AB7;background:#E8EEFF;padding:4px 12px;border-radius:6px;display:inline-block;">{clave_temporal}</span>
              </td>
            </tr>
          </table>
          <p style="margin:12px 0 0;color:#888;font-size:12px;">⚠ Cópiala tal como aparece, sin espacios</p>
        </div>
        <p style="color:#666;font-size:13px;">
          Por seguridad, te recomendamos cambiar la contraseña desde la sección
          <strong>Ajustes</strong> de la app una vez que ingreses.
        </p>
        <p style="color:#888;font-size:12px;margin-top:16px;">
          Si no esperabas este correo, contáctate con el administrador de tu empresa.
        </p>
        """,
        empresa_nombre,
    )
    enviar_email(email, f'Tu acceso a FlotaSystem — {empresa_nombre}', html)


# ── Seguridad — Reset de contraseña ──────────────────────────────────────────

def email_reset_password(email, nombre, empresa_nombre, clave_temporal, url_login):
    """Aviso al usuario con contraseña temporal generada por un administrador."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_reset_password:
        return
    html = _base_template(
        'Tu contraseña fue restablecida',
        f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">
          Un administrador restableció tu contraseña en <strong>{empresa_nombre}</strong>.
        </p>
        <div style="background:#F0F4FF;border-radius:8px;padding:20px;margin:16px 0;text-align:center;">
          <p style="margin:0 0 8px;color:#666;font-size:13px;">Tu contraseña temporal es:</p>
          <p style="margin:0;font-family:monospace,Courier New,monospace;font-size:26px;font-weight:700;color:#534AB7;background:#E8EEFF;padding:10px 20px;border-radius:6px;display:inline-block;">
{clave_temporal}</p>
          <p style="margin:8px 0 0;color:#888;font-size:12px;">⚠ Cópiala tal como aparece, sin espacios</p>
        </div>
        <p style="color:#888;font-size:13px;">
          Por seguridad, cambia esta contraseña inmediatamente después de ingresar.
        </p>
        {_btn('Ingresar al panel', url_login)}
        <p style="color:#c0392b;font-size:13px;margin-top:16px;">
          ⚠ Si no solicitaste este cambio, contacta al administrador de inmediato.
        </p>
        """,
        empresa_nombre,
    )
    return enviar_email(email, f'Contraseña restablecida — {empresa_nombre}', html)


# ── Pagos pendientes — Recordatorio ──────────────────────────────────────────

def email_recordatorio_pago(email, nombre, empresa_nombre, plan_nombre,
                             dias_pendiente, url_pago):
    """
    Recordatorio a empresas con suscripción en estado 'pendiente'
    que aún no han completado su primer pago.
    """
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not config.notif_recordatorio_pago:
        return
    html = _base_template(
        'Completa tu suscripción',
        f"""
        <p style="color:#444;font-size:15px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#444;font-size:15px;">
          Notamos que tu empresa <strong>{empresa_nombre}</strong> aún no ha
          completado el pago para activar el plan <strong>{plan_nombre}</strong>.
        </p>
        <div style="background:#FAEEDA;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:0;color:#633806;font-size:14px;">
            ⏳ Han pasado <strong>{dias_pendiente} días</strong> desde que se creó
            tu cuenta. Activa tu plan ahora para acceder a todas las funciones.
          </p>
        </div>
        {_btn('Activar mi plan', url_pago, '#BA7517')}
        <p style="color:#888;font-size:13px;">
          Si ya realizaste el pago o tienes dudas, contacta a nuestro soporte.
        </p>
        """,
        empresa_nombre,
    )
    enviar_email(email, f'Completa tu suscripción — {empresa_nombre}', html)


# ── Bienvenida (nuevo registro) ───────────────────────────────────────────────

def email_bienvenida(email, nombre, empresa_nombre, plan_nombre, url_dashboard):
    """Email de bienvenida enviado tras el primer pago aprobado de una empresa nueva."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.get()
    if not getattr(config, 'notif_bienvenida', True):
        return
    html = _base_template(
        f'¡Bienvenido a FlotaSystem, {nombre}!',
        f"""
        <p style="color:#444;font-size:15px;margin:0 0 16px;">
          Tu empresa <strong>{empresa_nombre}</strong> ya está activa en FlotaSystem.
          Tu plan <strong>{plan_nombre}</strong> está listo para usar.
        </p>
        <div style="background:#f0f4ff;border-radius:8px;padding:16px 20px;margin:16px 0;">
          <p style="margin:0 0 8px;font-weight:600;color:#1a1a1a;font-size:14px;">
            Primeros pasos recomendados:
          </p>
          <ol style="margin:0;padding-left:20px;color:#444;font-size:14px;line-height:1.8;">
            <li>Crea tu primera flota de vehículos</li>
            <li>Agrega tus vehículos y conductores</li>
            <li>Configura las reglas de mantención predictiva</li>
            <li>Descarga la app móvil para tus conductores</li>
          </ol>
        </div>
        {_btn('Ir al panel de control', url_dashboard)}
        <p style="color:#888;font-size:13px;margin-top:16px;">
          Si tienes dudas, contacta a nuestro equipo de soporte en cualquier momento.
        </p>
        """,
        empresa_nombre,
    )
    enviar_email(email, f'¡Bienvenido a FlotaSystem! Tu cuenta está lista', html)
