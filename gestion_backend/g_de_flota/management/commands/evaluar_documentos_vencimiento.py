from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from g_de_flota.models import Documento, Empresa, TipoNotificacion, Notificacion
from g_de_flota.notificaciones import notificar_admins_empresa

UMBRAL_DIAS = 30


class Command(BaseCommand):
    help = 'Notifica documentos próximos a vencer o vencidos.'

    def handle(self, *args, **kwargs):
        hoy   = timezone.now().date()
        limite = hoy + timedelta(days=UMBRAL_DIAS)
        tipos_label = dict(Documento.TODOS_TIPOS)
        notificadas = 0

        for empresa in Empresa.objects.filter(estado='activa'):
            docs = Documento.objects.filter(
                empresa=empresa,
                fecha_vencimiento__isnull=False,
                fecha_vencimiento__lte=limite,
            ).select_related('vehiculo', 'conductor')

            for doc in docs:
                dias     = (doc.fecha_vencimiento - hoy).days
                tipo     = TipoNotificacion.DOCUMENTO_VENCIDO if dias <= 0 else TipoNotificacion.DOCUMENTO_POR_VENCER
                doc_key  = f"doc_{doc.id}"

                ya_notificado = Notificacion.objects.filter(
                    extra__doc_key=doc_key,
                    fecha__date=hoy,
                ).exists()
                if ya_notificado:
                    continue

                label = tipos_label.get(doc.tipo, doc.tipo)
                fecha_str = doc.fecha_vencimiento.strftime('%d/%m/%Y')

                if doc.entidad == 'vehiculo' and doc.vehiculo:
                    patente = doc.vehiculo.patente
                    titulo  = f"Documento por vencer: {patente}"
                    mensaje = f"{label} del vehículo {patente} vence el {fecha_str} ({dias} días)."
                    url     = '/empresa/flota'
                    extra   = {'doc_key': doc_key, 'vehiculo_id': doc.vehiculo.id}
                elif doc.entidad == 'conductor' and doc.conductor:
                    nombre  = doc.conductor.nombre or doc.conductor.email
                    titulo  = f"Documento por vencer: {nombre}"
                    mensaje = f"{label} del conductor {nombre} vence el {fecha_str} ({dias} días)."
                    url     = '/empresa/conductores'
                    extra   = {'doc_key': doc_key, 'conductor_id': doc.conductor.id}
                else:
                    continue

                notificar_admins_empresa(empresa, tipo, titulo, mensaje, url_accion=url, extra=extra)
                notificadas += 1

        self.stdout.write(self.style.SUCCESS(
            f'Evaluación completada. Notificaciones enviadas: {notificadas}'
        ))
