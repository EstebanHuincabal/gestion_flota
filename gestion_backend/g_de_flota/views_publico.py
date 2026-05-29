"""
views_publico.py — Endpoints públicos sin autenticación.

Expone dos recursos para el flujo de auto-registro de empresas:

  GET  /api/planes/         Lista los planes activos con precios y límites.
  POST /api/auto-registro/  Crea empresa + usuario administrador + suscripción
                            pendiente, y devuelve un JWT listo para usar en el
                            pago inmediato con Transbank.
"""

import hashlib
import logging

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Empresa, Usuario, PlanSuscripcion, Suscripcion, CambioPlan,
    Rol, normalizar_rut, REGIONES_CHILE,
    TipoNotificacion,
)
from .audit import registrar_log
from .notificaciones import notificar_admins_empresa

logger = logging.getLogger(__name__)

_REGIONES_CODIGOS = {code for code, _ in REGIONES_CHILE}


# ─────────────────────────────────────────
# GET /api/verificar-rut/
# ─────────────────────────────────────────

class VerificarRutView(APIView):
    """
    Verifica si un RUT ya está registrado en el sistema.

    Un RUT es un identificador único nacional, por lo que se verifica en AMBAS
    tablas (Empresa y Usuario): un mismo RUT no puede pertenecer a la vez a una
    empresa y a una persona. El parámetro `tipo` se mantiene por compatibilidad
    pero no altera la verificación cruzada.

    Query params:
        rut  — RUT a verificar (con o sin puntos y guión)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        rut_raw = request.query_params.get('rut', '').strip()

        if not rut_raw:
            return Response({'disponible': True})

        rut_norm = normalizar_rut(rut_raw)
        rut_hash = hashlib.sha256(rut_norm.encode()).hexdigest()

        existe = (
            Empresa.objects.filter(rut_hash=rut_hash).exists() or
            Usuario.objects.filter(rut_hash=rut_hash).exists()
        )

        return Response({
            'disponible': not existe,
            'mensaje':    'Este RUT ya está registrado en el sistema.' if existe else '',
        })


# ─────────────────────────────────────────
# GET /api/planes/
# ─────────────────────────────────────────

class PlanesPublicosView(APIView):
    """Lista los planes de suscripción activos, ordenados para mostrar en landing."""

    permission_classes = [AllowAny]

    def get(self, request):
        planes = PlanSuscripcion.objects.filter(activo=True).order_by('orden', 'id')
        data = []
        for p in planes:
            data.append({
                'id':              p.id,
                'nombre':          p.nombre,
                'nombre_display':  p.get_nombre_display(),
                'descripcion':     p.descripcion,
                'precio_mensual':  str(p.precio_mensual) if p.precio_mensual else None,
                'precio_anual':    str(p.precio_anual)   if p.precio_anual   else None,
                'max_flotas':      p.max_flotas,
                'max_vehiculos':   p.max_vehiculos,
                'max_conductores': p.max_conductores,
                'max_usuarios':    p.max_usuarios,
                'modulos':         p.modulos or [],
            })
        return Response(data)


# ─────────────────────────────────────────
# POST /api/auto-registro/
# ─────────────────────────────────────────

class AutoRegistroView(APIView):
    """
    Registro público de empresa + usuario administrador.

    Recibe en un solo request los datos de la empresa, del usuario admin y
    el plan elegido. Crea todo en una transacción atómica y devuelve un JWT
    para que el frontend pueda iniciar el pago inmediatamente.

    Body esperado::

        {
          "empresa": {
            "nombre":   "Transportes XYZ",
            "rut":      "12.345.678-9",
            "email":    "contacto@xyz.cl",    // opcional
            "telefono": "912345678",           // opcional
            "region":   "metropolitana"        // opcional
          },
          "usuario": {
            "nombre_completo": "Juan Pérez",
            "rut":             "98.765.432-1",
            "email":           "juan@xyz.cl",
            "password":        "Segura123"
          },
          "plan_id": 2,
          "ciclo":   "mensual"
        }

    Respuesta exitosa (201)::

        {
          "access":     "<JWT access token>",
          "refresh":    "<JWT refresh token>",
          "user":       { id, nombre, email, rol, empresa, empresa_id, ... },
          "empresa_id": 42
        }
    """

    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        body    = request.data
        emp_d   = body.get('empresa', {})
        usr_d   = body.get('usuario', {})
        plan_id = body.get('plan_id')
        ciclo   = body.get('ciclo', 'mensual')

        # ── Validaciones básicas de campos requeridos ────────────────────────
        errores = {}

        if not emp_d.get('nombre', '').strip():
            errores['empresa_nombre'] = 'El nombre de la empresa es obligatorio.'
        elif len(emp_d.get('nombre', '').strip()) > 30:
            errores['empresa_nombre'] = 'El nombre de la empresa no puede superar los 30 caracteres.'

        if len(emp_d.get('direccion', '').strip()) > 40:
            errores['empresa_direccion'] = 'La dirección no puede superar los 40 caracteres.'

        if not usr_d.get('nombre', '').strip():
            errores['usuario_nombre'] = 'El nombre del administrador es obligatorio.'
        if not usr_d.get('apellido_paterno', '').strip():
            errores['usuario_apellido_paterno'] = 'El apellido paterno es obligatorio.'
        if not usr_d.get('apellido_materno', '').strip():
            errores['usuario_apellido_materno'] = 'El apellido materno es obligatorio.'
        if not usr_d.get('email', '').strip():
            errores['usuario_email'] = 'El correo electrónico del administrador es obligatorio.'
        if not usr_d.get('password', ''):
            errores['usuario_password'] = 'La contraseña es obligatoria.'
        if not usr_d.get('telefono', '').strip():
            errores['usuario_telefono'] = 'El teléfono del administrador es obligatorio.'
        if not plan_id:
            errores['plan_id'] = 'Debes seleccionar un plan.'
        if ciclo not in ('mensual', 'anual'):
            errores['ciclo'] = 'El ciclo debe ser mensual o anual.'

        if errores:
            return Response({'errores': errores}, status=status.HTTP_400_BAD_REQUEST)

        # ── Validar y normalizar RUT empresa ─────────────────────────────────
        # Un RUT es único globalmente: se verifica en ambas tablas (Empresa y Usuario).
        rut_emp_raw = emp_d.get('rut', '').strip()
        if rut_emp_raw:
            rut_emp_norm = normalizar_rut(rut_emp_raw)
            cuerpo_emp   = rut_emp_norm.split('-')[0] if '-' in rut_emp_norm else rut_emp_norm
            if not cuerpo_emp.isdigit() or len(cuerpo_emp) < 7:
                return Response(
                    {'error': 'El RUT de la empresa es demasiado corto. Verifica el número.',
                     'campo': 'empresa_rut'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            rut_emp_hash = hashlib.sha256(rut_emp_norm.encode()).hexdigest()
            if (Empresa.objects.filter(rut_hash=rut_emp_hash).exists() or
                    Usuario.objects.filter(rut_hash=rut_emp_hash).exists()):
                return Response(
                    {'error': 'Este RUT ya está registrado en el sistema.',
                     'campo': 'empresa_rut'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            rut_emp_norm = None
            rut_emp_hash = None

        # ── Validar y normalizar RUT usuario ─────────────────────────────────
        rut_usr_raw = usr_d.get('rut', '').strip()
        if rut_usr_raw:
            rut_usr_norm = normalizar_rut(rut_usr_raw)
            cuerpo_usr   = rut_usr_norm.split('-')[0] if '-' in rut_usr_norm else rut_usr_norm
            if not cuerpo_usr.isdigit() or len(cuerpo_usr) < 7:
                return Response(
                    {'error': 'El RUT del administrador es demasiado corto. Verifica el número.',
                     'campo': 'usuario_rut'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # No permitir el mismo RUT para la empresa y el administrador
            if rut_emp_norm and rut_usr_norm == rut_emp_norm:
                return Response(
                    {'error': 'El RUT del administrador no puede ser el mismo que el de la empresa.',
                     'campo': 'usuario_rut'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            rut_usr_hash = hashlib.sha256(rut_usr_norm.encode()).hexdigest()
            if (Usuario.objects.filter(rut_hash=rut_usr_hash).exists() or
                    Empresa.objects.filter(rut_hash=rut_usr_hash).exists()):
                return Response(
                    {'error': 'Este RUT ya está registrado en el sistema.',
                     'campo': 'usuario_rut'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            rut_usr_norm = None

        # ── Validar email usuario único ───────────────────────────────────────
        email_usr = usr_d.get('email', '').strip().lower()
        if Usuario.objects.filter(email__iexact=email_usr).exists():
            return Response(
                {'error': 'Ya existe una cuenta con ese correo electrónico.',
                 'campo': 'usuario_email'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Validar plan ──────────────────────────────────────────────────────
        try:
            plan = PlanSuscripcion.objects.get(pk=plan_id, activo=True)
        except PlanSuscripcion.DoesNotExist:
            return Response(
                {'error': 'El plan seleccionado no está disponible.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Validar región ───────────────────────────────────────────────────
        region = emp_d.get('region', '')
        if region and region not in _REGIONES_CODIGOS:
            region = ''

        # ── Crear Empresa ────────────────────────────────────────────────────
        empresa = Empresa(
            nombre=emp_d.get('nombre', '').strip(),
            region=region,
            pais=emp_d.get('pais', 'Chile').strip() or 'Chile',
            estado='activa',
            plan=plan,
        )
        if rut_emp_norm:
            empresa.set_rut(rut_emp_norm)
        email_emp = emp_d.get('email', '').strip()
        if email_emp:
            empresa.set_email(email_emp)
        telefono_emp = emp_d.get('telefono', '').strip()
        if telefono_emp:
            empresa.set_telefono(telefono_emp)
        direccion_emp = emp_d.get('direccion', '').strip()
        if direccion_emp:
            empresa.set_direccion(direccion_emp)
        comuna_emp = emp_d.get('comuna', '').strip()
        if comuna_emp:
            empresa.set_comuna(comuna_emp)
        ciudad_emp = emp_d.get('ciudad', '').strip()
        if ciudad_emp:
            empresa.set_ciudad(ciudad_emp)
        empresa.save()

        # ── Crear Usuario administrador ──────────────────────────────────────
        nombre_usr     = usr_d.get('nombre', '').strip().title()
        ap_paterno_usr = usr_d.get('apellido_paterno', '').strip().title()
        ap_materno_usr = usr_d.get('apellido_materno', '').strip().title()
        telefono_usr   = usr_d.get('telefono', '').strip()
        nombre_completo_usr = ' '.join(p for p in [nombre_usr, ap_paterno_usr, ap_materno_usr] if p)

        usuario = Usuario.objects.create_user(
            email=email_usr,
            rut=rut_usr_norm or email_usr,
            nombre_completo=nombre_completo_usr,
            password=usr_d.get('password'),
            rol=Rol.USUARIO,
            empresa=empresa,
            primer_login=True,
        )
        usuario.set_nombre_partes(nombre_usr, ap_paterno_usr, ap_materno_usr)
        if telefono_usr:
            usuario.set_telefono(telefono_usr)
        usuario.save()

        # ── Crear Suscripción en estado pendiente (activa tras el pago) ──────
        Suscripcion.objects.create(
            empresa=empresa,
            plan=plan,
            ciclo=ciclo,
            estado='pendiente',
        )

        # ── Historial de cambio de plan ───────────────────────────────────────
        CambioPlan.objects.create(
            empresa=empresa,
            plan_antes=None,
            plan_despues=plan,
            cambiado_por=None,
            motivo='Auto-registro público',
        )

        # ── Registrar en auditoría ────────────────────────────────────────────
        try:
            registrar_log(
                'ACTIVIDAD', 'auto_registro', request,
                usuario=usuario,
                detalle={
                    'empresa':   empresa.nombre,
                    'plan':      plan.nombre,
                    'ciclo':     ciclo,
                    'empresa_id': empresa.id,
                },
            )
        except Exception:
            pass

        # ── Generar JWT para el pago inmediato ────────────────────────────────
        refresh   = RefreshToken.for_user(usuario)
        plan_mods = plan.modulos or []
        plan_perms = list(plan.permisos.values_list('codigo', flat=True))

        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id':           usuario.id,
                'nombre':       usuario.nombre or usuario.email,
                'email':        usuario.email,
                'rol':          usuario.rol,
                'primer_login': usuario.primer_login,
                'empresa':      empresa.nombre,
                'empresa_id':   empresa.id,
                'plan_modulos': plan_mods,
                'plan_nombre':  plan.get_nombre_display(),
                'plan_permisos': plan_perms,
            },
            'empresa_id': empresa.id,
        }, status=status.HTTP_201_CREATED)
