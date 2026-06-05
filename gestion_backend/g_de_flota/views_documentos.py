import logging
import os

from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import FileResponse
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

logger = logging.getLogger(__name__)

from .models import (
    Documento, Empresa, Vehiculo, Usuario, Rol, TipoNotificacion, Notificacion,
    Asignacion,
)
from .audit import registrar_log, _diff_campos, _snap
from .notificaciones import notificar_admins_empresa


# ── Helpers ────────────────────────────────────────────────────

def _es_superadmin(user):
    return getattr(user, 'rol', None) == Rol.SUPERADMIN


def _get_empresa(user, params, fallback=None):
    if _es_superadmin(user):
        eid = params.get('empresa_id') if hasattr(params, 'get') else None
        if not eid and fallback and hasattr(fallback, 'get'):
            eid = fallback.get('empresa_id')
        if eid:
            try:
                return Empresa.objects.get(pk=eid)
            except Empresa.DoesNotExist:
                return None
        return None
    return user.empresa


def _to_iso(val):
    """Convierte date o str ISO a str ISO, tolerante a ambos tipos."""
    if not val:
        return None
    return val if isinstance(val, str) else val.isoformat()


_PEOR = {'vencido': 0, 'por_vencer': 1, 'vigente': 2, 'sin_vencimiento': 3}


def _estado_peor(estados):
    if not estados:
        return 'sin_vencimiento'
    return min(estados, key=lambda s: _PEOR.get(s, 99))


def _doc_dict(doc):
    return {
        'id':                doc.id,
        'entidad':           doc.entidad,
        'tipo':              doc.tipo,
        'tipo_display':      doc.get_tipo_display(),
        'vehiculo_id':       doc.vehiculo_id,
        'vehiculo_patente':  doc.vehiculo.patente if doc.vehiculo else None,
        'conductor_id':      doc.conductor_id,
        'conductor_nombre':  doc.conductor.nombre if doc.conductor else None,
        'fecha_emision':     _to_iso(doc.fecha_emision),
        'fecha_vencimiento': _to_iso(doc.fecha_vencimiento),
        'dias_para_vencer':  doc.dias_para_vencer(),
        'estado':            doc.estado(),
        'tiene_archivo':     bool(doc.archivo),
        'nombre_archivo':    doc.nombre_archivo or '',
        'subido_por_nombre': doc.subido_por.nombre if doc.subido_por else None,
        'notas':             doc.notas,
        'version_anterior_id': doc.version_anterior_id,
        'created_at':        doc.created_at.isoformat(),
    }


def _build_resumen(qs):
    docs = list(qs.select_related('vehiculo', 'conductor'))

    total      = len(docs)
    vigentes   = sum(1 for d in docs if d.estado() == 'vigente')
    por_vencer = sum(1 for d in docs if d.estado() == 'por_vencer')
    vencidos   = sum(1 for d in docs if d.estado() == 'vencido')

    alertas_docs = [d for d in docs if d.estado() in ('vencido', 'por_vencer')]
    alertas_docs.sort(key=lambda d: (
        0 if d.estado() == 'vencido' else 1,
        d.dias_para_vencer() if d.dias_para_vencer() is not None else 0,
    ))
    alertas = [
        {
            'id':               d.id,
            'tipo_display':     d.get_tipo_display(),
            'entidad_nombre':   d.vehiculo.patente if d.vehiculo else (d.conductor.nombre if d.conductor else ''),
            'fecha_vencimiento': d.fecha_vencimiento.isoformat() if d.fecha_vencimiento else None,
            'dias_para_vencer': d.dias_para_vencer(),
            'estado':           d.estado(),
        }
        for d in alertas_docs[:30]
    ]

    # Agrupación por vehículo
    veh_map = {}
    for d in docs:
        if d.vehiculo_id:
            key = d.vehiculo_id
            if key not in veh_map:
                veh_map[key] = {'vehiculo_id': key, 'patente': d.vehiculo.patente if d.vehiculo else '', 'estados': [], 'total': 0}
            veh_map[key]['estados'].append(d.estado())
            veh_map[key]['total'] += 1

    por_vehiculo = [
        {
            'vehiculo_id': v['vehiculo_id'],
            'patente':     v['patente'],
            'total':       v['total'],
            'esperados':   3,
            'estado_peor': _estado_peor(v['estados']),
        }
        for v in veh_map.values()
    ]

    # Agrupación por conductor
    cond_map = {}
    for d in docs:
        if d.conductor_id:
            key = d.conductor_id
            if key not in cond_map:
                cond_map[key] = {'conductor_id': key, 'nombre': d.conductor.nombre if d.conductor else '', 'estados': [], 'total': 0}
            cond_map[key]['estados'].append(d.estado())
            cond_map[key]['total'] += 1

    por_conductor = [
        {
            'conductor_id': c['conductor_id'],
            'nombre':       c['nombre'],
            'total':        c['total'],
            'esperados':    2,
            'estado_peor':  _estado_peor(c['estados']),
        }
        for c in cond_map.values()
    ]

    return {
        'total':         total,
        'vigentes':      vigentes,
        'por_vencer':    por_vencer,
        'vencidos':      vencidos,
        'alertas':       alertas,
        'por_vehiculo':  por_vehiculo,
        'por_conductor': por_conductor,
    }


def _vehiculo_asignado_id(user):
    """Devuelve el vehiculo_id activo del conductor, o None."""
    asig = Asignacion.objects.filter(conductor=user, activo=True).only('vehiculo_id').first()
    return asig.vehiculo_id if asig else None


def _qs_empresa(user, params):
    if user.rol == Rol.CONDUCTOR:
        # Docs propios del conductor + docs del vehículo que tiene asignado
        vid = _vehiculo_asignado_id(user)
        if vid:
            qs = Documento.objects.filter(Q(conductor=user) | Q(vehiculo_id=vid))
        else:
            qs = Documento.objects.filter(conductor=user)
        return qs, None
    empresa = _get_empresa(user, params)
    if not empresa:
        return None, None
    return Documento.objects.filter(empresa=empresa), empresa


# ── Vistas ─────────────────────────────────────────────────────

class DocumentosListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs, empresa = _qs_empresa(request.user, request.query_params)
        if qs is None:
            return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

        entidad    = request.query_params.get('entidad')
        tipo       = request.query_params.get('tipo')
        estado     = request.query_params.get('estado')
        vid        = request.query_params.get('vehiculo_id')
        cid        = request.query_params.get('conductor_id')
        buscar     = request.query_params.get('buscar', '').strip()

        if entidad: qs = qs.filter(entidad=entidad)
        if tipo:    qs = qs.filter(tipo=tipo)
        if vid:     qs = qs.filter(vehiculo_id=vid)
        if cid:     qs = qs.filter(conductor_id=cid)
        if buscar:
            qs = qs.filter(Q(tipo__icontains=buscar) | Q(nombre_archivo__icontains=buscar))

        qs = qs.select_related('vehiculo', 'conductor', 'subido_por')
        docs = list(qs.order_by('-created_at'))

        if estado:
            docs = [d for d in docs if d.estado() == estado]

        return Response({
            'documentos': [_doc_dict(d) for d in docs],
            'resumen':    _build_resumen(qs),
        })

    def post(self, request):
        user    = request.user
        data    = request.data
        archivo = request.FILES.get('archivo')

        if user.rol == Rol.CONDUCTOR:
            empresa = user.empresa
            entidad_req = data.get('entidad')
            if entidad_req == 'conductor':
                if str(data.get('conductor_id')) != str(user.id):
                    return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)
            elif entidad_req == 'vehiculo':
                vid = data.get('vehiculo_id')
                asig = Asignacion.objects.filter(conductor=user, activo=True, vehiculo_id=vid).first()
                if not asig:
                    return Response(
                        {'error': 'Sin permisos. El vehículo no está asignado a ti.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            else:
                return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            empresa = _get_empresa(user, data, fallback=request.query_params)
            if not empresa:
                return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

        entidad = data.get('entidad')
        tipo    = data.get('tipo')

        if entidad not in ('vehiculo', 'conductor'):
            return Response({'error': 'Entidad inválida.'}, status=status.HTTP_400_BAD_REQUEST)

        tipos_v = [t[0] for t in Documento.TIPOS_VEHICULO]
        tipos_c = [t[0] for t in Documento.TIPOS_CONDUCTOR]

        if entidad == 'vehiculo' and tipo not in tipos_v:
            return Response({'error': f'Tipo "{tipo}" no es válido para vehículos.'}, status=status.HTTP_400_BAD_REQUEST)
        if entidad == 'conductor' and tipo not in tipos_c:
            return Response({'error': f'Tipo "{tipo}" no es válido para conductores.'}, status=status.HTTP_400_BAD_REQUEST)

        vehiculo  = None
        conductor = None

        if entidad == 'vehiculo':
            vid = data.get('vehiculo_id')
            if not vid:
                return Response({'error': 'Se requiere vehiculo_id.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                vehiculo = Vehiculo.objects.get(pk=vid, empresa=empresa)
            except Vehiculo.DoesNotExist:
                return Response({'error': 'Vehículo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            cid = data.get('conductor_id')
            if not cid:
                return Response({'error': 'Se requiere conductor_id.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                conductor = Usuario.objects.get(pk=cid, empresa=empresa, rol=Rol.CONDUCTOR)
            except Usuario.DoesNotExist:
                return Response({'error': 'Conductor no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        doc = Documento(
            empresa=empresa,
            entidad=entidad,
            tipo=tipo,
            vehiculo=vehiculo,
            conductor=conductor,
            fecha_emision=parse_date(data['fecha_emision']) if data.get('fecha_emision') else None,
            fecha_vencimiento=parse_date(data['fecha_vencimiento']) if data.get('fecha_vencimiento') else None,
            notas=data.get('notas', ''),
            subido_por=user,
        )

        if archivo:
            doc.archivo        = archivo
            doc.nombre_archivo = archivo.name

        pid = data.get('version_anterior_id')
        if pid:
            try:
                doc.version_anterior = Documento.objects.get(pk=pid, empresa=empresa)
            except Documento.DoesNotExist:
                pass

        doc.save()

        registrar_log('ACTIVIDAD', 'documento_subido', request, detalle={
            'documento_id':      doc.id,
            'tipo':              doc.get_tipo_display(),
            'entidad':           entidad,
            'nombre_archivo':    doc.nombre_archivo or None,
            'vehiculo_patente':  doc.vehiculo.patente if doc.vehiculo else None,
            'conductor_nombre':  doc.conductor.nombre if doc.conductor else None,
            'fecha_emision':     str(doc.fecha_emision) if doc.fecha_emision else None,
            'fecha_vencimiento': str(doc.fecha_vencimiento) if doc.fecha_vencimiento else None,
            'notas':             doc.notas or None,
        })

        if user.rol == Rol.CONDUCTOR:
            notificar_admins_empresa(
                empresa=empresa,
                tipo=TipoNotificacion.ACTIVIDAD,
                titulo='Conductor subió un documento',
                mensaje=f'El conductor {user.nombre} subió "{doc.get_tipo_display()}".',
                url_accion='/empresa/documentos',
                permiso='documentos.ver',
            )

        return Response(_doc_dict(doc), status=status.HTTP_201_CREATED)


class DocumentoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, user, doc_id):
        try:
            if user.rol == Rol.CONDUCTOR:
                vid = _vehiculo_asignado_id(user)
                f   = Q(conductor=user) | Q(vehiculo_id=vid) if vid else Q(conductor=user)
                return Documento.objects.select_related('vehiculo', 'conductor', 'subido_por').get(f, pk=doc_id)
            if _es_superadmin(user):
                return Documento.objects.select_related('vehiculo', 'conductor', 'subido_por').get(pk=doc_id)
            return Documento.objects.select_related('vehiculo', 'conductor', 'subido_por').get(pk=doc_id, empresa=user.empresa)
        except Documento.DoesNotExist:
            return None

    def get(self, request, doc_id):
        doc = self._get(request.user, doc_id)
        if not doc:
            return Response({'error': 'Documento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_doc_dict(doc))

    def put(self, request, doc_id):
        doc = self._get(request.user, doc_id)
        if not doc:
            return Response({'error': 'Documento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        data    = request.data
        archivo = request.FILES.get('archivo')

        _campos_doc = ['fecha_emision', 'fecha_vencimiento', 'notas', 'nombre_archivo']
        _antes_doc  = _snap(doc, _campos_doc)

        if data.get('fecha_emision'):     doc.fecha_emision     = parse_date(data['fecha_emision'])
        if data.get('fecha_vencimiento'): doc.fecha_vencimiento = parse_date(data['fecha_vencimiento'])
        if 'notas' in data:               doc.notas             = data['notas']

        if archivo:
            if doc.archivo:
                try: default_storage.delete(doc.archivo.name)
                except Exception: pass
            doc.archivo        = archivo
            doc.nombre_archivo = archivo.name

        doc.save()
        registrar_log('ACTIVIDAD', 'documento_editado', request, detalle={
            'documento_id':      doc.id,
            'tipo':              doc.get_tipo_display(),
            'nombre_archivo':    doc.nombre_archivo or None,
            'vehiculo_patente':  doc.vehiculo.patente if doc.vehiculo else None,
            'conductor_nombre':  doc.conductor.nombre if doc.conductor else None,
            'fecha_vencimiento': str(doc.fecha_vencimiento) if doc.fecha_vencimiento else None,
            'cambios':           _diff_campos(_antes_doc, _snap(doc, _campos_doc)),
        })
        return Response(_doc_dict(doc))

    def delete(self, request, doc_id):
        user = request.user
        doc  = self._get(user, doc_id)
        if not doc:
            return Response({'error': 'Documento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        puede = (
            _es_superadmin(user) or
            user == doc.subido_por or
            (user.rol == Rol.USUARIO and user.empresa_id == doc.empresa_id)
        )
        if not puede:
            return Response({'error': 'Sin permisos para eliminar.'}, status=status.HTTP_403_FORBIDDEN)

        if doc.archivo:
            try: default_storage.delete(doc.archivo.name)
            except Exception: pass

        registrar_log('ACTIVIDAD', 'documento_eliminado', request, detalle={
            'documento_id':     doc.id,
            'tipo':             doc.get_tipo_display(),
            'nombre_archivo':   doc.nombre_archivo or None,
            'vehiculo_patente': doc.vehiculo.patente if doc.vehiculo else None,
            'conductor_nombre': doc.conductor.nombre if doc.conductor else None,
        })
        doc.delete()
        return Response({'message': 'Documento eliminado.'})


class DocumentoDescargarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        user = request.user
        try:
            if user.rol == Rol.CONDUCTOR:
                vid = _vehiculo_asignado_id(user)
                f   = Q(conductor=user) | Q(vehiculo_id=vid) if vid else Q(conductor=user)
                doc = Documento.objects.get(f, pk=doc_id)
            elif _es_superadmin(user):
                doc = Documento.objects.get(pk=doc_id)
            else:
                doc = Documento.objects.get(pk=doc_id, empresa=user.empresa)
        except Documento.DoesNotExist:
            return Response({'error': 'Documento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not doc.archivo:
            return Response({'error': 'Este documento no tiene archivo adjunto.'}, status=status.HTTP_404_NOT_FOUND)

        registrar_log('ACTIVIDAD', 'documento_descargado', request, detalle={
            'documento_id':     doc.id,
            'tipo':             doc.get_tipo_display(),
            'nombre_archivo':   doc.nombre_archivo or None,
            'vehiculo_patente': doc.vehiculo.patente if doc.vehiculo else None,
            'conductor_nombre': doc.conductor.nombre if doc.conductor else None,
        })

        try:
            archivo = doc.archivo.open('rb')
            nombre  = doc.nombre_archivo or os.path.basename(doc.archivo.name)
            return FileResponse(archivo, as_attachment=True, filename=nombre)
        except FileNotFoundError:
            return Response(
                {'error': 'El archivo ya no existe en el servidor.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            logger.error(
                'Error al servir documento pk=%s (archivo=%s): %s',
                doc.id, doc.archivo.name, exc, exc_info=True,
            )
            return Response({'error': 'No se pudo servir el archivo.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentoRenovarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, doc_id):
        user    = request.user
        archivo = request.FILES.get('archivo')

        if not archivo:
            return Response({'error': 'El archivo es obligatorio para renovar.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if _es_superadmin(user):
                anterior = Documento.objects.get(pk=doc_id)
            else:
                anterior = Documento.objects.get(pk=doc_id, empresa=user.empresa if user.rol != Rol.CONDUCTOR else user.empresa)
        except Documento.DoesNotExist:
            return Response({'error': 'Documento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        data    = request.data
        nuevo   = Documento(
            empresa=anterior.empresa,
            entidad=anterior.entidad,
            tipo=anterior.tipo,
            vehiculo=anterior.vehiculo,
            conductor=anterior.conductor,
            fecha_emision=parse_date(data['fecha_emision']) if data.get('fecha_emision') else None,
            fecha_vencimiento=parse_date(data['fecha_vencimiento']) if data.get('fecha_vencimiento') else None,
            notas=data.get('notas', ''),
            subido_por=user,
            version_anterior=anterior,
            archivo=archivo,
            nombre_archivo=archivo.name,
        )
        nuevo.save()

        registrar_log('ACTIVIDAD', 'documento_renovado', request, detalle={
            'documento_id':      nuevo.id,
            'tipo':              nuevo.get_tipo_display(),
            'anterior_id':       anterior.id,
            'nombre_archivo':    nuevo.nombre_archivo or None,
            'vehiculo_patente':  nuevo.vehiculo.patente if nuevo.vehiculo else None,
            'conductor_nombre':  nuevo.conductor.nombre if nuevo.conductor else None,
            'fecha_emision':     str(nuevo.fecha_emision) if nuevo.fecha_emision else None,
            'fecha_vencimiento': str(nuevo.fecha_vencimiento) if nuevo.fecha_vencimiento else None,
        })

        return Response(_doc_dict(nuevo), status=status.HTTP_201_CREATED)
