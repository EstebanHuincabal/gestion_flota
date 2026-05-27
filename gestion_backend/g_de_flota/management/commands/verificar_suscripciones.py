"""
Comando de gestión para verificar el estado de las suscripciones.
Ejecutar diariamente con cron: 0 9 * * * python manage.py verificar_suscripciones

Lógica:
  - Suscripción activa y vencida → pasar a período de gracia
  - En gracia sin pago → suspender empresa si bloqueo_automatico=True
  - Activa y falta 3 días + tarjeta guardada → cobro automático OneClick
  - Activa próxima a vencer → notificación a 30, 15, 7, 3, 1 días
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings


class Command(BaseCommand):
    help = 'Verifica el estado de las suscripciones y aplica bloqueos / cobros automáticos'

    def handle(self, *args, **kwargs):
        from g_de_flota.models import Suscripcion, ConfiguracionSistema, PagoTransbank, TarjetaGuardada, Usuario
        from g_de_flota.notificaciones import notificar_admins_empresa
        import uuid

        config = ConfiguracionSistema.get()
        ahora  = timezone.now()

        # ── Recordatorios de pago para suscripciones pendientes ──────────────
        DIAS_RECORDATORIO_PENDIENTE = [3, 7, 14, 30]
        pendientes = Suscripcion.objects.filter(
            estado='pendiente',
        ).select_related('empresa', 'plan')

        for sus in pendientes:
            dias_pendiente = (ahora - sus.created_at).days
            if dias_pendiente in DIAS_RECORDATORIO_PENDIENTE:
                notificar_admins_empresa(
                    empresa=sus.empresa,
                    tipo='actividad',
                    titulo='Recuerda activar tu plan',
                    mensaje=(
                        f'Han pasado {dias_pendiente} días desde que creaste tu cuenta y aún '
                        f'no has completado el pago para el plan {sus.plan.get_nombre_display()}. '
                        f'Activa tu plan para acceder a todas las funciones.'
                    ),
                )
                try:
                    from g_de_flota.email_service import email_recordatorio_pago
                    admins = Usuario.objects.filter(
                        empresa=sus.empresa, rol='USUARIO', is_active=True,
                    )
                    for admin in admins:
                        email_recordatorio_pago(
                            email=admin.email,
                            nombre=admin.nombre or admin.email,
                            empresa_nombre=sus.empresa.nombre,
                            plan_nombre=sus.plan.get_nombre_display(),
                            dias_pendiente=dias_pendiente,
                            url_pago=f"{settings.FRONTEND_URL}/empresa/pago",
                        )
                except Exception:
                    pass
                self.stdout.write(
                    f'  [RECORDATORIO] {sus.empresa.nombre} — pendiente hace {dias_pendiente} días.'
                )

        suscripciones = Suscripcion.objects.filter(
            estado__in=['activa', 'gracia'],
        ).select_related('empresa', 'plan')

        procesadas = 0

        for sus in suscripciones:

            if not sus.fecha_fin_periodo:
                continue

            dias = (sus.fecha_fin_periodo - ahora).days

            # ── Activa y vencida → período de gracia ─────────────────────────
            if sus.estado == 'activa' and dias <= 0:
                sus.estado = 'gracia'
                sus.save()
                notificar_admins_empresa(
                    empresa=sus.empresa,
                    tipo='seguridad',
                    titulo='Suscripción vencida — período de gracia iniciado',
                    mensaje=(
                        f'Tu suscripción venció. Tienes {config.dias_gracia_pago} días para '
                        f'regularizar el pago antes de que el servicio sea suspendido.'
                    ),
                )
                # Email período de gracia
                try:
                    from g_de_flota.email_service import email_suscripcion_gracia
                    admins = Usuario.objects.filter(
                        empresa=sus.empresa, rol='USUARIO', is_active=True,
                    )
                    for admin in admins:
                        email_suscripcion_gracia(
                            email=admin.email,
                            nombre=admin.nombre or admin.email,
                            empresa_nombre=sus.empresa.nombre,
                            dias_gracia_restantes=config.dias_gracia_pago,
                            url_pago=f"{settings.FRONTEND_URL}/empresa/pago",
                        )
                except Exception:
                    pass
                self.stdout.write(
                    f'  [GRACIA]    {sus.empresa.nombre} — venció, período de gracia iniciado.'
                )
                procesadas += 1

            # ── En gracia: evaluar suspensión ─────────────────────────────────
            elif sus.estado == 'gracia':
                dias_en_gracia = (ahora - sus.fecha_fin_periodo).days
                if dias_en_gracia >= config.dias_gracia_pago and config.bloqueo_automatico:
                    sus.estado = 'suspendida'
                    sus.empresa.estado = 'suspendida'
                    sus.empresa.save(update_fields=['estado'])
                    sus.save()
                    notificar_admins_empresa(
                        empresa=sus.empresa,
                        tipo='seguridad',
                        titulo='Servicio suspendido por falta de pago',
                        mensaje=config.mensaje_pago_pendiente,
                    )
                    # Email servicio suspendido
                    try:
                        from g_de_flota.email_service import email_suscripcion_bloqueada
                        admins = Usuario.objects.filter(
                            empresa=sus.empresa, rol='USUARIO', is_active=True,
                        )
                        for admin in admins:
                            email_suscripcion_bloqueada(
                                email=admin.email,
                                nombre=admin.nombre or admin.email,
                                empresa_nombre=sus.empresa.nombre,
                                url_pago=f"{settings.FRONTEND_URL}/empresa/pago",
                            )
                    except Exception:
                        pass
                    self.stdout.write(
                        f'  [SUSPENDIDA] {sus.empresa.nombre} — suspendida por falta de pago.'
                    )
                    procesadas += 1

            # ── Activa con 3 días y tarjeta guardada → cobro automático ───────
            elif sus.estado == 'activa' and dias == 3:
                try:
                    tarjeta = sus.empresa.tarjeta_guardada
                except TarjetaGuardada.DoesNotExist:
                    tarjeta = None

                if tarjeta:
                    self._cobrar_automatico(sus, tarjeta, ahora)
                    procesadas += 1

                # Notificar de todas formas (con o sin tarjeta)
                notificar_admins_empresa(
                    empresa=sus.empresa,
                    tipo='actividad',
                    titulo='Tu suscripción vence en 3 días',
                    mensaje=(
                        f'El plan {sus.plan.get_nombre_display()} vence el '
                        f'{sus.fecha_fin_periodo.strftime("%d/%m/%Y")}. '
                        + ('Se realizará cobro automático con tu tarjeta guardada.'
                           if tarjeta else 'Renueva para evitar interrupciones.')
                    ),
                )
                self.stdout.write(
                    f'  {"[AUTOCOBRO]" if tarjeta else "[AVISO]"}     '
                    f'{sus.empresa.nombre} — vence en 3 días.'
                )

            # ── Activa con vencimiento próximo → recordatorio ─────────────────
            elif sus.estado == 'activa' and dias in [30, 15, 7, 1]:
                notificar_admins_empresa(
                    empresa=sus.empresa,
                    tipo='actividad',
                    titulo=f'Tu suscripción vence en {dias} días',
                    mensaje=(
                        f'El plan {sus.plan.get_nombre_display()} vence el '
                        f'{sus.fecha_fin_periodo.strftime("%d/%m/%Y")}. '
                        f'Renueva para evitar interrupciones.'
                    ),
                )
                # Email vencimiento próximo
                try:
                    from g_de_flota.email_service import email_suscripcion_vence
                    admins = Usuario.objects.filter(
                        empresa=sus.empresa, rol='USUARIO', is_active=True,
                    )
                    for admin in admins:
                        email_suscripcion_vence(
                            email=admin.email,
                            nombre=admin.nombre or admin.email,
                            empresa_nombre=sus.empresa.nombre,
                            plan_nombre=sus.plan.get_nombre_display(),
                            dias=dias,
                            fecha_vencimiento=sus.fecha_fin_periodo.strftime('%d/%m/%Y'),
                            url_pago=f"{settings.FRONTEND_URL}/empresa/pago",
                        )
                except Exception:
                    pass
                self.stdout.write(
                    f'  [AVISO]     {sus.empresa.nombre} — vence en {dias} días.'
                )
                procesadas += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Suscripciones verificadas. {procesadas} empresa(s) notificadas o actualizadas.'
            )
        )

    def _cobrar_automatico(self, sus, tarjeta, ahora):
        """Intenta cobrar la renovación con OneClick Mall."""
        from g_de_flota.models import PagoTransbank
        from g_de_flota.notificaciones import notificar_admins_empresa
        from g_de_flota.views_planes import _get_oneclick_transaction
        import uuid

        plan  = sus.plan
        monto = int(plan.precio_anual if sus.ciclo == 'anual' else plan.precio_mensual or 0)
        if not monto:
            self.stdout.write(f'  [AUTOCOBRO SKIP] {sus.empresa.nombre} — sin monto configurado.')
            return

        orden_compra = f"AUTO-{sus.empresa.id}-{uuid.uuid4().hex[:8].upper()}"
        child_order  = f"CHD-{sus.empresa.id}-{uuid.uuid4().hex[:8].upper()}"

        try:
            tx      = _get_oneclick_transaction()
            oc_resp = tx.authorize(
                user_name=tarjeta.username_tb,
                tbk_user=tarjeta.tbk_user,
                parent_buy_order=orden_compra,
                details=[{
                    'commerce_code':       settings.ONECLICK_CHILD_CODE,
                    'buy_order':           child_order,
                    'amount':              monto,
                    'installments_number': 1,
                }],
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'  [AUTOCOBRO ERROR] {sus.empresa.nombre} — {e}'
            ))
            notificar_admins_empresa(
                empresa=sus.empresa,
                tipo='seguridad',
                titulo='Error en cobro automático',
                mensaje='No se pudo realizar el cobro automático. Por favor renueva manualmente.',
            )
            return

        # Verificar respuesta
        if isinstance(oc_resp, dict):
            details = oc_resp.get('details', [])
        else:
            details = getattr(oc_resp, 'details', [])

        det = details[0] if details else None
        if det:
            resp_code = det.get('response_code', -1) if isinstance(det, dict) else getattr(det, 'response_code', -1)
            auth_code = det.get('authorization_code', '') if isinstance(det, dict) else getattr(det, 'authorization_code', '')
        else:
            resp_code = -1
            auth_code = ''

        if resp_code != 0:
            self.stdout.write(self.style.WARNING(
                f'  [AUTOCOBRO RECHAZADO] {sus.empresa.nombre} — código {resp_code}'
            ))
            notificar_admins_empresa(
                empresa=sus.empresa,
                tipo='seguridad',
                titulo='Cobro automático rechazado',
                mensaje='Tu tarjeta fue rechazada. Por favor renueva manualmente antes del vencimiento.',
            )
            return

        # Pago aprobado → renovar suscripción
        PagoTransbank.objects.create(
            empresa=sus.empresa, suscripcion=sus,
            token=f"AUTO-{orden_compra}",
            orden_compra=orden_compra,
            monto=monto, ciclo=sus.ciclo,
            plan_nombre=plan.get_nombre_display(),
            estado='aprobado',
            fecha_pago=ahora,
            respuesta_tb={'auth_code': auth_code, 'response_code': resp_code, 'via': 'autocobro'},
        )

        sus.estado = 'activa'
        sus.fecha_inicio      = ahora
        sus.fecha_fin_periodo = (
            ahora + timezone.timedelta(days=365)
            if sus.ciclo == 'anual'
            else ahora + timezone.timedelta(days=30)
        )
        sus.save()

        self.stdout.write(self.style.SUCCESS(
            f'  [AUTOCOBRO OK] {sus.empresa.nombre} — {monto:,} CLP cobrados, renovada hasta '
            f'{sus.fecha_fin_periodo.strftime("%d/%m/%Y")}.'
        ))
        notificar_admins_empresa(
            empresa=sus.empresa,
            tipo='actividad',
            titulo='Suscripción renovada automáticamente',
            mensaje=(
                f'Se cobró {monto:,} CLP con tu tarjeta '
                f'({tarjeta.card_type} ****{tarjeta.last_4}). '
                f'Próximo vencimiento: {sus.fecha_fin_periodo.strftime("%d/%m/%Y")}.'
            ),
        )
