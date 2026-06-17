from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from g_de_flota.models import Documento, TipoNotificacion, Notificacion, Usuario
from g_de_flota.notificaciones import notificar_admins_empresa

UMBRALES_DIAS = [30, 15, 7, 1]


class Command(BaseCommand):
    help = 'Notifica documentos unificados próximos a vencer o ya vencidos (ejecutar diariamente).'

    def handle(self, *args, **kwargs):
        hoy         = timezone.now().date()
        notificadas = 0

        documentos = Documento.objects.filter(
            fecha_vencimiento__isnull=False,
            empresa__estado='activa',
        ).select_related('empresa', 'vehiculo', 'conductor')

        for doc in documentos:
            dias = doc.dias_para_vencer()
            if dias is None:
                continue

            entidad_nombre = (
                doc.vehiculo.patente if doc.vehiculo
                else (doc.conductor.nombre if doc.conductor else '—')
            )
            doc_key = f"doc_nuevo_{doc.id}"

            if dias < 0:
                ya = Notificacion.objects.filter(
                    tipo=TipoNotificacion.DOCUMENTO_VENCIDO,
                    extra__doc_key=doc_key,
                    fecha__date=hoy,
                ).exists()
                if ya:
                    continue

                notificar_admins_empresa(
                    empresa=doc.empresa,
                    tipo=TipoNotificacion.DOCUMENTO_VENCIDO,
                    titulo=f'Documento vencido: {doc.get_tipo_display()}',
                    mensaje=(
                        f'El documento "{doc.get_tipo_display()}" de {entidad_nombre} '
                        f'venció hace {abs(dias)} día{"s" if abs(dias) != 1 else ""}.'
                    ),
                    url_accion='/empresa/documentos',
                    extra={'doc_key': doc_key, 'documento_id': doc.id, 'dias': dias},
                    permiso='documentos.ver',
                )
                # Email documento vencido
                try:
                    from g_de_flota.email_service import email_documento_vence
                    admins = Usuario.objects.filter(
                        empresa=doc.empresa, rol='USUARIO', is_active=True,
                    )
                    for admin in admins:
                        email_documento_vence(
                            email=admin.email,
                            nombre=admin.nombre or admin.email,
                            empresa_nombre=doc.empresa.nombre,
                            tipo_documento=doc.get_tipo_display(),
                            entidad_nombre=entidad_nombre,
                            dias=dias,
                            fecha_vencimiento=doc.fecha_vencimiento.strftime('%d/%m/%Y'),
                            url_documentos=f"{settings.FRONTEND_URL}/empresa/documentos",
                        )
                except Exception:
                    pass
                notificadas += 1

            elif dias in UMBRALES_DIAS:
                ya = Notificacion.objects.filter(
                    tipo=TipoNotificacion.DOCUMENTO_POR_VENCER,
                    extra__doc_key=doc_key,
                    extra__dias_umbral=dias,
                ).exists()
                if ya:
                    continue

                notificar_admins_empresa(
                    empresa=doc.empresa,
                    tipo=TipoNotificacion.DOCUMENTO_POR_VENCER,
                    titulo=f'Documento por vencer: {doc.get_tipo_display()}',
                    mensaje=(
                        f'El documento "{doc.get_tipo_display()}" de {entidad_nombre} '
                        f'vence en {dias} día{"s" if dias != 1 else ""} '
                        f'({doc.fecha_vencimiento.strftime("%d/%m/%Y")}).'
                    ),
                    url_accion='/empresa/documentos',
                    extra={'doc_key': doc_key, 'documento_id': doc.id, 'dias': dias, 'dias_umbral': dias},
                    permiso='documentos.ver',
                )
                # Email documento por vencer
                try:
                    from g_de_flota.email_service import email_documento_vence
                    admins = Usuario.objects.filter(
                        empresa=doc.empresa, rol='USUARIO', is_active=True,
                    )
                    for admin in admins:
                        email_documento_vence(
                            email=admin.email,
                            nombre=admin.nombre or admin.email,
                            empresa_nombre=doc.empresa.nombre,
                            tipo_documento=doc.get_tipo_display(),
                            entidad_nombre=entidad_nombre,
                            dias=dias,
                            fecha_vencimiento=doc.fecha_vencimiento.strftime('%d/%m/%Y'),
                            url_documentos=f"{settings.FRONTEND_URL}/empresa/documentos",
                        )
                except Exception:
                    pass
                notificadas += 1

        self.stdout.write(self.style.SUCCESS(
            f'Verificación completada. Notificaciones enviadas: {notificadas}'
        ))
