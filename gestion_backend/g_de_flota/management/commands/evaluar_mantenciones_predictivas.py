from django.core.management.base import BaseCommand
from django.utils import timezone
from g_de_flota.models import VehiculoPlan, MantencionProgramada, AlertaMantencion, TipoNotificacion, Rol, Usuario
from g_de_flota.notificaciones import notificar_admins_empresa

class Command(BaseCommand):
    help = 'Evalúa los planes de mantenimiento y genera alertas si corresponde.'

    def handle(self, *args, **kwargs):
        hoy = timezone.now().date()
        vehiculos_planes = VehiculoPlan.objects.filter(
            vehiculo__activo=True,
            plan__activo=True
        ).select_related('vehiculo', 'plan').prefetch_related('plan__reglas')

        alertas_creadas = 0

        for vp in vehiculos_planes:
            for regla in vp.plan.reglas.all():
                # Obtener o crear la programación para este vehículo y regla
                prog, created = MantencionProgramada.objects.get_or_create(
                    vehiculo=vp.vehiculo,
                    regla=regla,
                    defaults={
                        'fecha_ultima': vp.fecha_asignacion.date(),
                        'fecha_siguiente': vp.fecha_asignacion.date() + timezone.timedelta(days=regla.intervalo_dias),
                        'estado': 'activa'
                    }
                )

                if prog.estado != 'activa':
                    continue

                dias_transcurridos = (hoy - prog.fecha_ultima).days
                dias_restantes = (prog.fecha_siguiente - hoy).days
                
                # Evitar división por cero
                if regla.intervalo_dias > 0:
                    pct_avance = (dias_transcurridos / regla.intervalo_dias) * 100
                else:
                    pct_avance = 100.0

                # Verificar si cae en el umbral
                if dias_restantes <= regla.umbral_alerta_dias:
                    # Verificar si ya existe una alerta pendiente para esta programación
                    alerta_existente = AlertaMantencion.objects.filter(
                        mantencion_programada=prog,
                        atendida=False
                    ).first()

                    nivel = 'vencida' if dias_restantes <= 0 else 'por_vencer'

                    if not alerta_existente:
                        AlertaMantencion.objects.create(
                            mantencion_programada=prog,
                            nivel=nivel,
                            dias_restantes=dias_restantes,
                            pct_avance=round(pct_avance, 2)
                        )
                        alertas_creadas += 1
                        tipo_notif = (TipoNotificacion.MANTENCION_VENCIDA
                                      if nivel == 'vencida'
                                      else TipoNotificacion.MANTENCION_POR_VENCER)
                        empresa = prog.vehiculo.empresa
                        notificar_admins_empresa(
                            empresa, tipo_notif,
                            f"Mantención {nivel.replace('_', ' ')}: {prog.vehiculo.patente}",
                            f"El vehículo {prog.vehiculo.patente} requiere '{prog.regla.tipo}'. "
                            f"Días restantes: {dias_restantes}.",
                            url_accion='/empresa/predictivo',
                            extra={'vehiculo_id': prog.vehiculo.id}
                        )
                        
                    elif alerta_existente.nivel != nivel:
                        # Actualizar si pasó de por_vencer a vencida
                        alerta_existente.nivel = nivel
                        alerta_existente.dias_restantes = dias_restantes
                        alerta_existente.pct_avance = round(pct_avance, 2)
                        alerta_existente.save()
                        
                    elif alerta_existente:
                        # Solo actualizar dias_restantes y pct_avance
                        alerta_existente.dias_restantes = dias_restantes
                        alerta_existente.pct_avance = round(pct_avance, 2)
                        alerta_existente.save()
                        
                        # Escalar si han pasado 48h sin atención
                        if regla.escalar_sin_respuesta and not alerta_existente.atendida:
                            dias_desde_alerta = (timezone.now() - alerta_existente.fecha_creacion).days
                            if dias_desde_alerta >= 2:
                                empresa = prog.vehiculo.empresa
                                notificar_admins_empresa(
                                    empresa,
                                    TipoNotificacion.MANTENCION_VENCIDA,
                                    f"⚠ Alerta sin atender: {prog.vehiculo.patente}",
                                    f"La alerta de '{prog.regla.tipo}' para el vehículo {prog.vehiculo.patente} "
                                    f"lleva {dias_desde_alerta} días sin ser atendida.",
                                    url_accion='/empresa/predictivo',
                                    extra={'vehiculo_id': prog.vehiculo.id, 'alerta_id': alerta_existente.id}
                                )

        self.stdout.write(self.style.SUCCESS(f'Evaluación completada. Alertas creadas: {alertas_creadas}'))
