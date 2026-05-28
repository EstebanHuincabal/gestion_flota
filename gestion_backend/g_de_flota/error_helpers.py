"""
error_helpers.py — Utilidades centralizadas de manejo de errores para la API REST.

Proporciona tres herramientas complementarias:

  1. ``error_response``  — Construye respuestas JSON de error con estructura uniforme.
  2. ``validar_campos``  — Verifica que un dict tenga los campos obligatorios.
  3. ``vista_segura``    — Decorador que envuelve métodos de vista-clase con un
                           manejador global de excepciones, garantizando que ningún
                           500 no controlado llegue como HTML al cliente SPA.

Códigos de error estándar utilizados en todo el sistema
--------------------------------------------------------
  SIN_AUTENTICACION   401  Token inválido o expirado.
  SIN_PERMISO         403  Rol insuficiente para la operación.
  NO_ENCONTRADO       404  Recurso inexistente.
  VALIDACION          400  Campo faltante o con formato incorrecto.
  LIMITE_PLAN         403  Límite de recursos del plan alcanzado.
  MODULO_NO_INCLUIDO  403  Módulo no disponible en el plan actual.
  SUSCRIPCION_BLOQUEADA 402 Empresa sin suscripción activa.
  ERROR_INTERNO       500  Excepción no controlada en el servidor.
"""

import json
import traceback
from functools import wraps
from django.http import JsonResponse


def error_response(mensaje: str, codigo: str = None, status: int = 400, detalle=None) -> JsonResponse:
    """Construye una respuesta JSON de error con estructura uniforme.

    Todos los errores de la API siguen el mismo esquema para que el cliente
    pueda procesarlos de forma genérica:

    .. code-block:: json

        {
            "error":   "Descripción legible para el usuario.",
            "codigo":  "CODIGO_SEMANTICO",
            "detalle": { ... }
        }

    Los campos ``codigo`` y ``detalle`` son opcionales y solo se incluyen
    cuando se proporcionan, para mantener la respuesta mínima.

    Args:
        mensaje (str): Texto descriptivo del error, legible para el usuario final.
        codigo (str, optional): Código semántico en mayúsculas (p. ej. ``'LIMITE_PLAN'``).
            Permite al cliente distinguir el tipo de error sin parsear el mensaje.
        status (int, optional): Código HTTP de la respuesta. Por defecto ``400``.
        detalle (dict, optional): Información adicional estructurada sobre el error
            (p. ej. qué campos fallaron la validación). No se incluye si es ``None``.

    Returns:
        JsonResponse: Respuesta HTTP con ``Content-Type: application/json`` y el
            status indicado.

    Example:
        >>> return error_response(
        ...     'Has alcanzado el límite de flotas de tu plan.',
        ...     codigo='LIMITE_PLAN',
        ...     status=403,
        ...     detalle={'uso': 10, 'limite': 10},
        ... )
    """
    data = {'error': mensaje}
    if codigo:  data['codigo']  = codigo
    if detalle: data['detalle'] = detalle
    return JsonResponse(data, status=status)


def validar_campos(body: dict, requeridos: list) -> tuple[bool, str | None]:
    """Verifica que un dict tenga todos los campos requeridos con valor no vacío.

    Diseñado para usarse al inicio de cualquier vista POST/PUT antes de procesar
    el body, evitando ``KeyError`` y ``None`` en operaciones posteriores.

    Un campo se considera «faltante» si no existe en ``body`` o si su valor
    es falsy (``None``, ``''``, ``0``, ``False``, ``[]``). Ajusta la condición
    según el dominio si necesitas aceptar ``0`` o ``False`` como valores válidos.

    Args:
        body (dict): Diccionario con los datos enviados por el cliente,
            normalmente el resultado de ``json.loads(request.body)``.
        requeridos (list[str]): Lista de claves que deben estar presentes
            y tener valor no vacío.

    Returns:
        tuple[bool, str | None]: Par ``(valido, mensaje_error)``.
            - Si todos los campos están presentes → ``(True, None)``.
            - Si falta alguno → ``(False, "Campos requeridos faltantes: campo1, campo2")``.

    Example:
        >>> body = json.loads(request.body)
        >>> valido, msg = validar_campos(body, ['nombre', 'email', 'plan_id'])
        >>> if not valido:
        ...     return error_response(msg, 'VALIDACION', 400)
    """
    faltantes = [c for c in requeridos if not body.get(c)]
    if faltantes:
        return False, f"Campos requeridos faltantes: {', '.join(faltantes)}"
    return True, None


def vista_segura(func):
    """Decorador que envuelve métodos de vistas-clase con manejo global de excepciones.

    Garantiza que ningún error no controlado devuelva una página HTML de error 500
    al cliente SPA, que espera siempre JSON. Debe aplicarse sobre métodos de instancia
    (``get``, ``post``, ``put``, ``delete``) de clases que hereden de ``View`` o
    ``APIView``.

    Excepciones capturadas
    ----------------------
    ``json.JSONDecodeError``
        Se produce cuando el body de la petición no es JSON válido.
        Respuesta: 400 ``VALIDACION``.

    ``PermissionError``
        Lanzada manualmente por helpers de autorización (p. ej. ``get_empresa``).
        Respuesta: 403 ``SIN_PERMISO``.

    ``Exception`` (cualquier otra)
        Error inesperado. Se registra en ``LogAuditoria`` con tipo ``SEGURIDAD``
        y los últimos 800 caracteres del traceback para facilitar el diagnóstico.
        Respuesta: 500 ``ERROR_INTERNO``.

    Note:
        Al capturar ``Exception`` genérico, los errores de programación (NameError,
        AttributeError, etc.) son absorbidos en producción y registrados en los logs.
        En desarrollo conviene revisar ``LogAuditoria`` o los logs de Django.

    Args:
        func: Método de vista a decorar (debe recibir ``self, request, *args, **kwargs``).

    Returns:
        Callable: Versión decorada del método con manejo de errores incorporado.

    Example:
        >>> class MiVista(View):
        ...     @vista_segura
        ...     def post(self, request):
        ...         body = json.loads(request.body)   # JSONDecodeError manejado
        ...         valido, msg = validar_campos(body, ['nombre'])
        ...         if not valido:
        ...             return error_response(msg, 'VALIDACION')
        ...         ...
    """
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        try:
            return func(self, request, *args, **kwargs)

        except json.JSONDecodeError:
            return error_response(
                'El cuerpo de la petición no es JSON válido.',
                'VALIDACION',
                400,
            )

        except PermissionError as e:
            return error_response(str(e) or 'Sin permiso.', 'SIN_PERMISO', 403)

        except Exception as e:
            # Intentar registrar el error en auditoría antes de responder.
            # Se usa try/except propio para evitar que un fallo en el logging
            # impida devolver la respuesta de error al cliente.
            try:
                from .audit import registrar_log
                registrar_log(
                    'SEGURIDAD',
                    'error_interno',
                    request,
                    detalle={
                        'error':     str(e),
                        'vista':     func.__name__,
                        'traceback': traceback.format_exc()[-800:],
                    },
                )
            except Exception:
                pass

            return error_response(
                'Error interno del servidor. Intenta nuevamente.',
                'ERROR_INTERNO',
                500,
            )

    return wrapper
