from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from g_de_flota.models import (
    DocumentoVehiculo, DocumentoConductor, Empresa,
    TipoNotificacion, Notificacion,
)
from g_de_flota.notificaciones import notificar_admins_empresa

UMBRAL_DIAS = 30


class Command(BaseCommand):
    help = 'Notifica documentos de vehículos y conductores próximos a vencer.'

    def handle(self, *args, **kwargs):
        hoy = timezone.now().date()
        limite = hoy + timedelta(days=UMBRAL_DIAS)
        notificadas = 0

        for empresa in Empresa.objects.filter(estado='activa'):
            # Documentos de vehículos
            docs_vehiculo = DocumentoVehiculo.objects.filter(
                vehiculo__flota__empresa=empresa,
                fecha_vencimiento__gte=hoy,
                fecha_vencimiento__lte=limite,
            ).select_related('vehiculo')

            for doc in docs_vehiculo:
                dias = (doc.fecha_vencimiento - hoy).days
                tipo = TipoNotificacion.DOCUMENTO_VENCIDO if dias <= 0 else TipoNotificacion.DOCUMENTO_POR_VENCER
                doc_key = f"doc_vehiculo_{doc.id}"

                # Evitar notificar más de una vez por día el mismo documento
                ya_notificado = Notificacion.objects.filter(
                    extra__doc_key=doc_key,
                    fecha__date=hoy,
                ).exists()
                if ya_notificado:
                    continue

                notificar_admins_empresa(
                    empresa, tipo,
                    f"Documento por vencer: {doc.vehiculo.patente}",
                    f"{doc.get_tipo_display()} del vehículo {doc.vehiculo.patente} vence "
                    f"el {doc.fecha_vencimiento.strftime('%d/%m/%Y')} ({dias} días).",
                    url_accion='/empresa/flota',
                    extra={'doc_key': doc_key, 'vehiculo_id': doc.vehiculo.id}
                )
                notificadas += 1

            # Documentos de conductores
            docs_conductor = DocumentoConductor.objects.filter(
                conductor__empresa=empresa,
                fecha_vencimiento__gte=hoy,
                fecha_vencimiento__lte=limite,
            ).select_related('conductor')

            for doc in docs_conductor:
                dias = (doc.fecha_vencimiento - hoy).days
                tipo = TipoNotificacion.DOCUMENTO_VENCIDO if dias <= 0 else TipoNotificacion.DOCUMENTO_POR_VENCER
                doc_key = f"doc_conductor_{doc.id}"

                ya_notificado = Notificacion.objects.filter(
                    extra__doc_key=doc_key,
                    fecha__date=hoy,
                ).exists()
                if ya_notificado:
                    continue

                nombre_conductor = doc.conductor.nombre or doc.conductor.email
                notificar_admins_empresa(
                    empresa, tipo,
                    f"Documento por vencer: {nombre_conductor}",
                    f"{doc.get_tipo_display()} del conductor {nombre_conductor} vence "
                    f"el {doc.fecha_vencimiento.strftime('%d/%m/%Y')} ({dias} días).",
                    url_accion='/empresa/conductores',
                    extra={'doc_key': doc_key, 'conductor_id': doc.conductor.id}
                )
                notificadas += 1

        self.stdout.write(self.style.SUCCESS(
            f'Evaluación completada. Notificaciones enviadas: {notificadas}'
        ))
