Implementa el módulo completo de Mantenimiento Predictivo para el sistema
de gestión de flota vehicular que ya tenemos. El módulo vive en la ruta
/empresa/mantenciones y debe integrarse con el stack y convenciones que
ya existen en el proyecto.

El mantenimiento es exclusivamente por tiempo (días). No existe lógica
de kilometraje en ninguna parte del sistema.

## Funcionalidad requerida

### Planes de mantenimiento
- CRUD completo de planes. Cada plan tiene un nombre y se asigna a
  uno o varios vehículos.
- Cada plan contiene múltiples reglas. Cada regla define:
  - Tipo de mantención (aceite, frenos, neumáticos, filtros, RTV, etc.)
  - Prioridad: alta / media / baja
  - Intervalo en días (ej: cada 90 días, cada 365 días)
  - Umbral de alerta: alertar cuando falten X días para vencer
  - Canal de notificación por regla: email, push, WhatsApp, SMS
  - Flag: escalar a supervisor si no se atiende en 48h
  - Flag: bloquear despacho del vehículo si la mantención está vencida

### Motor de alertas automático
- Job programado que corre diariamente a las 07:00 y evalúa
  todos los vehículos activos con plan asignado.
- Por cada regla calcula los días transcurridos desde la última
  mantención y los días restantes hasta el vencimiento.
- Si los días restantes caen por debajo del umbral configurado
  y no existe ya una alerta pendiente, crea la alerta con nivel
  por_vencer o vencida (vencida cuando dias_restantes <= 0).
- Envía la notificación por el canal configurado en la regla.
- Si una alerta lleva más de 48h sin atenderse y tiene activo el
  flag de escalamiento, reenvía al supervisor.

### Alertas
- Vista con listado de alertas ordenadas por urgencia
  (vencidas primero, luego por días restantes ascendente).
- Cada alerta muestra: vehículo, tipo de mantención, nivel,
  días restantes (negativo si está vencida), porcentaje de avance
  del intervalo, fecha de vencimiento.
- Acciones por alerta: registrar mantención realizada (cierra la
  alerta, guarda la fecha de realización y calcula automáticamente
  la próxima fecha sumando el intervalo), programar para fecha
  futura, descartar.
- Filtros por nivel y por estado (pendiente / atendida).
- Panel de configuración de canales de notificación globales
  con toggles on/off.

### Simulador de vencimientos
- El usuario selecciona un vehículo y un período (3, 6 o 12 meses).
- El sistema proyecta todos los eventos de mantención que ocurrirán
  en ese período con fecha exacta estimada y costo estimado por evento.
- Muestra el total de eventos y el presupuesto total estimado
  para el período.

## Estructura de datos

Modelos necesarios:
- PlanMantenimiento → nombre, descripción, activo
- ReglaMantenimiento → FK plan, tipo, prioridad, intervalo_dias,
  umbral_alerta_dias, canal, escalar_sin_respuesta, bloquear_despacho,
  costo_estimado
- VehiculoPlan → FK vehículo, FK plan, fecha_asignacion
- MantencionProgramada → FK vehículo, FK regla, fecha_ultima,
  fecha_siguiente, estado
- AlertaMantencion → FK mantencion_programada, nivel, dias_restantes,
  pct_avance, enviada, atendida, fecha_creacion, fecha_atencion

El campo pct_avance se calcula como:
  dias_transcurridos / intervalo_dias * 100
donde dias_transcurridos = (hoy - fecha_ultima).days

## API

- CRUD de planes con reglas anidadas en el mismo payload
- Endpoint de alertas con filtros por nivel y estado
- Endpoint para atender una alerta: recibe fecha_realizada, guarda
  la mantención en el historial, actualiza fecha_ultima a hoy y
  calcula fecha_siguiente = hoy + intervalo_dias, cierra la alerta
- Endpoint de proyección: recibe vehículo y días del período,
  devuelve lista de eventos futuros con fecha exacta y costo estimado

## Permisos
- Solo rol admin_flota puede crear y editar planes
- Cualquier usuario autenticado puede ver las alertas de los
  vehículos que tiene asignados

## Frontend

Vista principal con 4 tabs: Planes, Nuevo Plan, Alertas, Simulador.

Componentes:
- Lista de planes con reglas expandibles y acciones editar/eliminar
- Formulario de plan con reglas dinámicas (agregar y quitar reglas
  sin recargar). El intervalo se expresa en días con un helper visual
  que muestra el equivalente en meses o años (ej: 90 días = 3 meses)
- Lista de alertas con barra de progreso, badges de nivel por color,
  días restantes destacados y acciones inline
- Simulador con selector de vehículo, selector de período y tabla
  de proyección reactiva con fechas exactas y costos

Genera todo el código completo en el orden: modelos → lógica de
negocio y job programado → API y rutas → componentes de frontend.
Sigue exactamente las convenciones y estructura de carpetas que
ya existen en el proyecto.