<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'

const logs      = ref([])
const cargando  = ref(true)
const count     = ref(0)
const numPages  = ref(1)
const page      = ref(1)

const filtros = ref({ tipo: '', accion: '', q: '', fecha_desde: '', fecha_hasta: '' })

// ── Panel de detalle ─────────────────────────────────────────
const logSeleccionado = ref(null)
const verDetalle = (log) => { logSeleccionado.value = log }
const cerrarDetalle = () => { logSeleccionado.value = null }

// ── Etiquetas ────────────────────────────────────────────────
const ACCION_LABELS = {
  // Seguridad
  login_exitoso:          'Login exitoso',
  login_fallido:          'Login fallido',
  cambio_password:        'Contraseña reseteada',
  password_cambiado:      'Contraseña cambiada',
  recuperar_password:           'Recuperación de contraseña',
  recuperar_password_conductor: 'Recuperación de contraseña (conductor)',
  cambio_rol:             'Cambio de rol',
  cambio_permisos:        'Permisos modificados',
  usuario_bloqueado:      'Usuario bloqueado',
  usuario_desbloqueado:   'Usuario desbloqueado',
  // Usuarios
  usuario_creado:         'Usuario creado',
  usuario_modificado:     'Usuario modificado',
  usuario_eliminado:      'Usuario eliminado',
  perfil_actualizado:     'Perfil actualizado',
  // Empresas
  auto_registro:          'Auto registro',
  empresa_creada:         'Empresa creada',
  empresa_suspendida:     'Empresa suspendida',
  empresa_eliminada:      'Empresa eliminada',
  // Planes
  plan_creado:            'Plan creado',
  plan_editado:           'Plan editado',
  plan_eliminado:         'Plan eliminado',
  plan_asignado:          'Plan asignado',
  plan_permisos_editados: 'Permisos de plan editados',
  solicitud_cambio_plan:  'Solicitud cambio de plan',
  upgrade_self_service:   'Mejora de plan (upgrade)',
  upgrade_webpay_aprobado:'Upgrade confirmado (Webpay)',
  downgrade_programado:   'Cambio de plan programado',
  downgrade_cancelado:    'Cambio de plan cancelado',
  // Flotas
  flota_creada:           'Flota creada',
  flota_editada:          'Flota editada',
  flota_eliminada:        'Flota eliminada',
  // Vehículos
  vehiculo_creado:        'Vehículo creado',
  vehiculo_editado:       'Vehículo editado',
  vehiculo_foto_conductor: 'Foto de vehículo (app)',
  vehiculo_desactivado:   'Vehículo desactivado',
  // Conductores
  conductor_creado:       'Conductor creado',
  conductor_editado:      'Conductor editado',
  conductor_desactivado:  'Conductor desactivado',
  conductor_asignado:     'Conductor asignado',
  conductor_desasignado:  'Conductor desasignado',
  // Mantenciones
  mantencion_creada:           'Mantención creada',
  mantencion_editada:          'Mantención editada',
  mantencion_eliminada:        'Mantención eliminada',
  mantencion_estado_cambiado:  'Estado de mantención cambiado',
  // Documentos
  documento_subido:       'Documento subido',
  documento_editado:      'Documento editado',
  documento_eliminado:    'Documento eliminado',
  documento_descargado:   'Documento descargado',
  documento_renovado:     'Documento renovado',
  // Solicitudes conductor
  solicitud_creada:                'Solicitud creada',
  solicitud_aprobada:              'Solicitud aprobada',
  solicitud_rechazada:             'Solicitud rechazada',
  // Mantenciones conductor
  mantencion_iniciada_conductor:   'Mantención iniciada por conductor',
  mantencion_completada_conductor: 'Mantención completada por conductor',
  // Rutas / checklist
  checklist_completado:            'Checklist pre-viaje completado',
  ruta_creada:            'Ruta creada',
  ruta_eliminada:         'Ruta eliminada',
  ruta_iniciada:          'Ruta iniciada',
  ruta_finalizada:        'Ruta finalizada',
  ruta_cancelada:         'Ruta cancelada',
  // Gastos
  gasto_creado:           'Gasto registrado',
  gasto_editado:          'Gasto editado',
  gasto_eliminado:        'Gasto eliminado',
  gasto_correctivo_registrado: 'Gasto correctivo registrado',
  gasto_correctivo_editado:    'Gasto correctivo editado',
  gasto_correctivo_eliminado:  'Gasto correctivo eliminado',
  presupuesto_creado:     'Presupuesto creado',
  presupuesto_editado:    'Presupuesto editado',
  // Predictivo
  crear_plan_mantenimiento:      'Plan predictivo creado',
  actualizar_plan_mantenimiento: 'Plan predictivo actualizado',
  eliminar_plan_mantenimiento:   'Plan predictivo eliminado',
  atender_alerta_mantencion:     'Alerta atendida',
  asignar_plan_vehiculo:         'Plan predictivo asignado',
  desasignar_plan_vehiculo:      'Plan predictivo desasignado',
  generar_alertas_predictivas:   'Alertas predictivas generadas',
  // Pagos y suscripción
  pago_iniciado:          'Pago iniciado',
  pago_aprobado:          'Pago aprobado',
  pago_oneclick:          'Pago con tarjeta guardada',
  pago_manual_registrado: 'Pago manual registrado',
  pago_error:             'Error de pago',
  pago_error_crear:       'Error al iniciar pago',
  oneclick_error:         'Error de cobro automático',
  suscripcion_reactivada: 'Suscripción reactivada',
  gracia_extendida:       'Período de gracia extendido',
  tarjeta_eliminada:      'Tarjeta eliminada',
  terminos_actualizados:  'Términos actualizados',
  // Email
  email_config_guardada:  'Configuración de correo guardada',
  email_test_enviado:     'Correo de prueba enviado',
  // GPS / Geolocalización
  gps_dispositivo_creado:    'Dispositivo GPS registrado',
  gps_dispositivo_editado:   'Dispositivo GPS editado',
  gps_dispositivo_eliminado: 'Dispositivo GPS eliminado',
  gps_asignado:              'GPS asignado a vehículo',
  gps_desasignado:           'GPS desasignado',
  gps_clave_regenerada:      'Clave de GPS regenerada',
  gps_config_guardada:       'Configuración GPS guardada',
  // App del conductor / sistema
  checklist_push_fallido: 'Fallo de notificación de checklist',
  excepcion_no_manejada:  'Error interno del servidor',
}

const ACCION_COLOR = {
  // Seguridad
  login_exitoso:          'verde',
  login_fallido:          'rojo',
  cambio_password:        'naranja',
  password_cambiado:      'naranja',
  cambio_rol:             'morado',
  cambio_permisos:        'morado',
  usuario_bloqueado:      'rojo',
  usuario_desbloqueado:   'verde',
  // Usuarios
  usuario_creado:         'azul',
  usuario_modificado:     'amarillo',
  usuario_eliminado:      'rojo',
  perfil_actualizado:     'amarillo',
  // Empresas
  auto_registro:          'azul',
  empresa_creada:         'azul',
  empresa_suspendida:     'naranja',
  empresa_eliminada:      'rojo',
  // Planes
  plan_creado:            'azul',
  plan_editado:           'amarillo',
  plan_eliminado:         'rojo',
  plan_asignado:          'verde',
  plan_permisos_editados: 'morado',
  solicitud_cambio_plan:  'naranja',
  // Flotas
  flota_creada:           'azul',
  flota_editada:          'amarillo',
  flota_eliminada:        'rojo',
  // Vehículos
  vehiculo_creado:        'azul',
  vehiculo_editado:       'amarillo',
  vehiculo_foto_conductor: 'amarillo',
  vehiculo_desactivado:   'naranja',
  // Conductores
  conductor_creado:       'azul',
  conductor_editado:      'amarillo',
  conductor_desactivado:  'naranja',
  conductor_asignado:     'verde',
  conductor_desasignado:  'naranja',
  // Mantenciones
  mantencion_creada:          'azul',
  mantencion_editada:         'amarillo',
  mantencion_eliminada:       'rojo',
  mantencion_estado_cambiado: 'morado',
  // Documentos
  documento_subido:       'azul',
  documento_editado:      'amarillo',
  documento_eliminado:    'rojo',
  documento_descargado:   'verde',
  documento_renovado:     'verde',
  // Solicitudes conductor
  solicitud_creada:                'azul',
  solicitud_aprobada:              'verde',
  solicitud_rechazada:             'rojo',
  // Mantenciones conductor
  mantencion_iniciada_conductor:   'naranja',
  mantencion_completada_conductor: 'verde',
  // Checklist
  checklist_completado:            'verde',
  // Rutas
  ruta_creada:            'azul',
  ruta_eliminada:         'rojo',
  ruta_iniciada:          'verde',
  ruta_finalizada:        'verde',
  ruta_cancelada:         'naranja',
  // Gastos
  gasto_creado:           'azul',
  gasto_editado:          'amarillo',
  gasto_eliminado:        'rojo',
  presupuesto_creado:     'azul',
  presupuesto_editado:    'amarillo',
  // Predictivo
  crear_plan_mantenimiento:      'azul',
  actualizar_plan_mantenimiento: 'amarillo',
  eliminar_plan_mantenimiento:   'rojo',
  atender_alerta_mantencion:     'verde',
  asignar_plan_vehiculo:         'verde',
  desasignar_plan_vehiculo:      'naranja',
  generar_alertas_predictivas:   'morado',
  // Pagos y suscripción
  pago_iniciado:          'azul',
  pago_aprobado:          'verde',
  pago_oneclick:          'verde',
  pago_manual_registrado: 'verde',
  pago_error:             'rojo',
  pago_error_crear:       'rojo',
  oneclick_error:         'rojo',
  suscripcion_reactivada: 'verde',
  gracia_extendida:       'naranja',
  tarjeta_eliminada:      'naranja',
  terminos_actualizados:  'morado',
  // Email
  email_config_guardada:  'amarillo',
  email_test_enviado:     'azul',
  // GPS / Geolocalización
  gps_dispositivo_creado:    'azul',
  gps_dispositivo_editado:   'amarillo',
  gps_dispositivo_eliminado: 'rojo',
  gps_asignado:              'verde',
  gps_desasignado:           'naranja',
  gps_clave_regenerada:      'morado',
  gps_config_guardada:       'amarillo',
  // App del conductor / sistema
  checklist_push_fallido: 'rojo',
  excepcion_no_manejada:  'rojo',
}

const GRUPOS_ACCIONES = {
  SEGURIDAD: [
    'login_exitoso','login_fallido','cambio_password','password_cambiado','cambio_rol',
    'cambio_permisos','usuario_bloqueado','usuario_desbloqueado',
    'recuperar_password','recuperar_password_conductor',
    'pago_error','pago_error_crear','oneclick_error','excepcion_no_manejada',
  ],
  ACTIVIDAD: [
    'usuario_creado','usuario_modificado','usuario_eliminado','perfil_actualizado',
    'auto_registro','empresa_creada','empresa_suspendida','empresa_eliminada',
    'plan_creado','plan_editado','plan_eliminado','plan_asignado','plan_permisos_editados','solicitud_cambio_plan',
    'upgrade_self_service','upgrade_webpay_aprobado','downgrade_programado','downgrade_cancelado',
    'flota_creada','flota_editada','flota_eliminada',
    'vehiculo_creado','vehiculo_editado','vehiculo_desactivado','vehiculo_foto_conductor',
    'conductor_creado','conductor_editado','conductor_desactivado','conductor_asignado','conductor_desasignado',
    'mantencion_creada','mantencion_editada','mantencion_eliminada','mantencion_estado_cambiado',
    'mantencion_iniciada_conductor','mantencion_completada_conductor',
    'documento_subido','documento_editado','documento_eliminado','documento_descargado','documento_renovado',
    'solicitud_creada','solicitud_aprobada','solicitud_rechazada',
    'checklist_completado',
    'ruta_creada','ruta_eliminada','ruta_iniciada','ruta_finalizada','ruta_cancelada',
    'gasto_creado','gasto_editado','gasto_eliminado',
    'gasto_correctivo_registrado','gasto_correctivo_editado','gasto_correctivo_eliminado',
    'presupuesto_creado','presupuesto_editado',
    'crear_plan_mantenimiento','actualizar_plan_mantenimiento','eliminar_plan_mantenimiento',
    'atender_alerta_mantencion','asignar_plan_vehiculo','desasignar_plan_vehiculo','generar_alertas_predictivas',
    'pago_iniciado','pago_aprobado','pago_oneclick','pago_manual_registrado',
    'suscripcion_reactivada','gracia_extendida','tarjeta_eliminada','terminos_actualizados',
    'email_config_guardada','email_test_enviado',
  ],
}

const accionesDisponibles = computed(() => {
  if (filtros.value.tipo === 'SEGURIDAD') return GRUPOS_ACCIONES.SEGURIDAD
  if (filtros.value.tipo === 'ACTIVIDAD') return GRUPOS_ACCIONES.ACTIVIDAD
  return [...GRUPOS_ACCIONES.SEGURIDAD, ...GRUPOS_ACCIONES.ACTIVIDAD]
})

// ── Detalle formateado ────────────────────────────────────────
const DETALLE_LABELS = {
  // ── Empresa ──────────────────────────────
  empresa_nombre:   'Empresa',
  empresa_id:       'ID Empresa',
  empresa:          'Empresa',

  // ── Usuario / Seguridad ──────────────────
  usuario_email:    'Usuario',
  usuario_id:       'ID Usuario',
  rol:              'Rol',
  rol_anterior:     'Rol anterior',
  rol_nuevo:        'Rol nuevo',
  permisos:         'Permisos',
  email:            'Email',
  nombre:           'Nombre',

  // ── Flota ────────────────────────────────
  flota_id:         'ID Flota',

  // ── Vehículo ─────────────────────────────
  vehiculo_id:      'ID Vehículo',
  vehiculo:         'Vehículo',
  patente:          'Patente',
  marca:            'Marca',
  modelo:           'Modelo',

  // ── Conductor ────────────────────────────
  conductor_id:     'ID Conductor',
  conductor:        'Conductor',

  // ── Mantención ───────────────────────────
  tipo:             'Tipo',
  tipo_mantencion:  'Tipo de mantención',
  estado_previo:    'Estado anterior',
  estado_nuevo:     'Estado nuevo',

  // ── Predictivo ───────────────────────────
  plan_id:          'ID Plan',
  asignacion_id:    'ID Asignación',
  alerta_id:        'ID Alerta',

  // ── Documentos ───────────────────────────
  documento_id:     'ID Documento',
  entidad:          'Entidad',
  nombre_archivo:   'Archivo',
  vehiculo_patente: 'Patente vehículo',
  conductor_nombre: 'Conductor',
  fecha_emision:    'Fecha de emisión',
  fecha_vencimiento:'Fecha de vencimiento',
  anterior_id:      'ID versión anterior',
  notas:            'Notas',

  // ── Gastos / Presupuesto ─────────────────
  gasto_id:         'ID Gasto',
  monto:            'Monto',
  categoria:        'Categoría',
  presupuesto_id:   'ID Presupuesto',
  mes:              'Mes',
  anio:             'Año',

  // ── Planes de suscripción ─────────────────
  plan:             'Plan',
  plan_solicitado:  'Plan solicitado',
  total:            'Total permisos',

  // ── Rutas ────────────────────────────────
  ruta_id:          'ID Ruta',
  km_inicio:        'Km inicial',
  km_reales:        'Km reales',
  costo_total_real: 'Costo total real',
  motivo:           'Motivo',

  // ── Generales ────────────────────────────
  fecha:            'Fecha',
  de:               'Desde',
  a:                'Hacia',
}

const detalleEntradas = computed(() => {
  if (!logSeleccionado.value?.detalle) return []
  return Object.entries(logSeleccionado.value.detalle)
    .filter(([k, v]) => !k.startsWith('_') && k !== 'cambios' && v !== null && v !== undefined && v !== '')
    .map(([k, v]) => ({
      clave: DETALLE_LABELS[k] || k,
      valor: Array.isArray(v) ? v.join(', ') : String(v),
    }))
})

// ── Carga ─────────────────────────────────────────────────────
const cargar = async () => {
  cargando.value = true
  const params = new URLSearchParams()
  if (filtros.value.tipo)        params.set('tipo',        filtros.value.tipo)
  if (filtros.value.accion)      params.set('accion',      filtros.value.accion)
  if (filtros.value.q)           params.set('q',           filtros.value.q)
  if (filtros.value.fecha_desde) params.set('fecha_desde', filtros.value.fecha_desde)
  if (filtros.value.fecha_hasta) params.set('fecha_hasta', filtros.value.fecha_hasta)
  params.set('page', page.value)

  const res = await apiFetch(`/api/logs/?${params.toString()}`)
  if (res.ok) {
    const data = await res.json()
    logs.value     = data.results
    count.value    = data.count
    numPages.value = data.num_pages
  }
  cargando.value = false
}

const aplicarFiltros = () => { page.value = 1; cargar() }
const limpiarFiltros = () => {
  filtros.value = { tipo: '', accion: '', q: '', fecha_desde: '', fecha_hasta: '' }
  page.value = 1; cargar()
}

watch(() => filtros.value.tipo, () => { filtros.value.accion = '' })
const irPagina = (n) => { page.value = n; cargar() }

const formatFecha = (f) =>
  new Date(f).toLocaleString('es-CL', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })

// El botón de detalle siempre aparece: navegador, SO, método y endpoint
// son campos de primer nivel y nunca están en log.detalle
const tieneDetalle = (_log) => true

const paginasVisibles = computed(() => {
  const total = numPages.value
  const cur   = page.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = new Set([1, total, cur, cur - 1, cur + 1].filter(n => n >= 1 && n <= total))
  return [...pages].sort((a, b) => a - b)
})

onMounted(cargar)
</script>

<template>
  <div class="page">

    <div class="page-header">
      <div>
        <h1 class="page-title">Logs y Auditoría</h1>
        <p class="page-subtitle">Trazabilidad de acciones del sistema · {{ count.toLocaleString('es-CL') }} registros</p>
      </div>
    </div>

    <!-- Filtros -->
    <div class="filtros-card">
      <div class="filtros-grid">
        <div class="filtro-item filtro-buscar">
          <label class="label-filtro">Buscar usuario / IP</label>
          <div class="input-icon-wrap">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input v-model="filtros.q" @keyup.enter="aplicarFiltros" type="text" placeholder="Email o dirección IP..." class="filter-input" />
          </div>
        </div>

        <div class="filtro-item">
          <label class="label-filtro">Tipo</label>
          <select v-model="filtros.tipo" @change="aplicarFiltros" class="filter-input">
            <option value="">Todos</option>
            <option value="SEGURIDAD">Seguridad</option>
            <option value="ACTIVIDAD">Actividad</option>
          </select>
        </div>

        <div class="filtro-item">
          <label class="label-filtro">Acción</label>
          <select v-model="filtros.accion" @change="aplicarFiltros" class="filter-input">
            <option value="">Todas las acciones</option>
            <option v-for="a in accionesDisponibles" :key="a" :value="a">{{ ACCION_LABELS[a] || a }}</option>
          </select>
        </div>

        <div class="filtro-item">
          <label class="label-filtro">Desde</label>
          <input v-model="filtros.fecha_desde" @change="aplicarFiltros" type="date" class="filter-input" />
        </div>

        <div class="filtro-item">
          <label class="label-filtro">Hasta</label>
          <input v-model="filtros.fecha_hasta" @change="aplicarFiltros" type="date" class="filter-input" />
        </div>

        <div class="filtro-btns">
          <button @click="aplicarFiltros" class="btn-primary">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            Buscar
          </button>
          <button @click="limpiarFiltros" class="btn-ghost">Limpiar</button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="cargando" class="loading">
      <div class="spinner"/>
      <span>Cargando logs...</span>
    </div>

    <!-- Tabla -->
    <div v-else class="tabla-card">
      <div class="tabla-scroll">
      <table class="tabla">
        <thead>
          <tr>
            <th style="width:130px">Fecha y Hora</th>
            <th style="width:96px">Tipo</th>
            <th style="width:200px">Acción</th>
            <th>Usuario</th>
            <th style="width:110px">IP</th>
            <th style="width:90px">Navegador</th>
            <th style="width:64px;text-align:center">Detalle</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="logs.length === 0">
            <td colspan="7" class="empty-row">No hay registros que coincidan con los filtros aplicados.</td>
          </tr>
          <tr v-for="log in logs" :key="log.id">
            <td class="td-fecha">{{ formatFecha(log.fecha) }}</td>
            <td>
              <span :class="['badge', log.tipo === 'SEGURIDAD' ? 'badge-seguridad' : 'badge-actividad']">
                {{ log.tipo === 'SEGURIDAD' ? 'Seguridad' : 'Actividad' }}
              </span>
            </td>
            <td>
              <span :class="['badge', `badge-${ACCION_COLOR[log.accion] || 'gris'}`]">
                {{ ACCION_LABELS[log.accion] || log.accion }}
              </span>
            </td>
            <td class="td-usuario">
              <span v-if="log.usuario_nombre" class="usr-nombre">{{ log.usuario_nombre }}</span>
              <span v-if="log.usuario_email" class="usr-email">{{ log.usuario_email }}</span>
              <span v-if="!log.usuario_nombre && !log.usuario_email">—</span>
            </td>
            <td class="td-mono">{{ log.ip || '—' }}</td>
            <td class="td-navegador">
              <span v-if="log.navegador" :class="['badge-navegador', `nav-${(log.navegador || 'otro').toLowerCase().replace(/\s/g,'_')}`]">
                {{ log.navegador }}
              </span>
              <span v-else class="td-sin-detalle">—</span>
            </td>
            <td style="text-align:center">
              <button
                v-if="tieneDetalle(log)"
                :class="['btn-detalle', { 'btn-detalle--activo': logSeleccionado?.id === log.id }]"
                @click="logSeleccionado?.id === log.id ? cerrarDetalle() : verDetalle(log)"
                title="Ver detalles"
              >
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
              </button>
              <span v-else class="td-sin-detalle">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <!-- Paginación -->
    <div v-if="numPages > 1" class="paginacion">
      <button :disabled="page === 1" @click="irPagina(page - 1)" class="pag-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
      </button>
      <template v-for="(n, i) in paginasVisibles" :key="n">
        <span v-if="i > 0 && paginasVisibles[i-1] !== n - 1" class="pag-dots">…</span>
        <button :class="['pag-num', { active: n === page }]" @click="irPagina(n)">{{ n }}</button>
      </template>
      <button :disabled="page === numPages" @click="irPagina(page + 1)" class="pag-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
      </button>
    </div>

    <!-- Modal de detalles -->
    <Teleport to="body">
      <div v-if="logSeleccionado" class="modal-overlay" @click.self="cerrarDetalle">
        <div class="modal-box">
          <div class="drag-handle"/>

          <!-- Header -->
          <div class="modal-header">
            <div class="modal-header-info">
              <span :class="['badge', `badge-${ACCION_COLOR[logSeleccionado.accion] || 'gris'}`]">
                {{ ACCION_LABELS[logSeleccionado.accion] || logSeleccionado.accion }}
              </span>
              <span class="modal-fecha">{{ formatFecha(logSeleccionado.fecha) }}</span>
            </div>
            <button class="modal-cerrar" @click="cerrarDetalle" title="Cerrar">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <!-- Cuerpo scrolleable -->
          <div class="modal-body">

            <!-- Descripción legible -->
            <p v-if="logSeleccionado.descripcion" class="modal-descripcion">
              {{ logSeleccionado.descripcion }}
            </p>

            <!-- Chips: tipo · usuario · IP · navegador · SO -->
            <div class="modal-chips">
              <span :class="['badge', logSeleccionado.tipo === 'SEGURIDAD' ? 'badge-seguridad' : 'badge-actividad']">
                {{ logSeleccionado.tipo === 'SEGURIDAD' ? 'Seguridad' : 'Actividad' }}
              </span>
              <span class="chip-info chip-usuario">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:12px;height:12px"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                <span v-if="logSeleccionado.usuario_nombre">{{ logSeleccionado.usuario_nombre }}</span>
                <span v-if="logSeleccionado.usuario_email" class="chip-email">{{ logSeleccionado.usuario_email }}</span>
                <span v-if="!logSeleccionado.usuario_nombre && !logSeleccionado.usuario_email">—</span>
              </span>
              <span class="chip-info chip-mono">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:12px;height:12px"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9"/></svg>
                {{ logSeleccionado.ip || '—' }}
              </span>
              <span v-if="logSeleccionado.navegador" :class="['badge-navegador', `nav-${(logSeleccionado.navegador).toLowerCase().replace(/\s/g,'_')}`]">
                {{ logSeleccionado.navegador }}
              </span>
              <span v-if="logSeleccionado.so" class="chip-info chip-so">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:12px;height:12px"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                {{ logSeleccionado.so }}
              </span>
            </div>

            <!-- Endpoint HTTP -->
            <div v-if="logSeleccionado.metodo" class="modal-endpoint">
              <span class="endpoint-metodo">{{ logSeleccionado.metodo }}</span>
              <span class="endpoint-path">{{ logSeleccionado.endpoint }}</span>
            </div>

            <!-- User-Agent completo -->
            <p v-if="logSeleccionado.user_agent" class="modal-ua" :title="logSeleccionado.user_agent">
              {{ logSeleccionado.user_agent }}
            </p>

            <!-- Tabla de cambios (antes → después) -->
            <template v-if="logSeleccionado.detalle?.cambios?.length">
              <p class="modal-section-title">Cambios realizados</p>
              <div class="modal-cambios">
                <div class="cambios-header">
                  <span>Campo</span><span>Antes</span><span>Después</span>
                </div>
                <div v-for="c in logSeleccionado.detalle.cambios" :key="c.campo" class="cambio-fila">
                  <span class="cambio-campo">{{ DETALLE_LABELS[c.campo] || c.campo }}</span>
                  <span class="cambio-antes">{{ c.antes || '—' }}</span>
                  <span class="cambio-despues">{{ c.despues || '—' }}</span>
                </div>
              </div>
            </template>

            <!-- Tabla de datos del evento (resto del detalle sin 'cambios') -->
            <template v-if="detalleEntradas.length">
              <p class="modal-section-title">Datos del evento</p>
              <div class="modal-filas">
                <div v-for="e in detalleEntradas" :key="e.clave" class="modal-fila">
                  <span class="modal-clave">{{ e.clave }}</span>
                  <span class="modal-valor">{{ e.valor }}</span>
                </div>
              </div>
            </template>
            <p v-else-if="!logSeleccionado.detalle?.cambios?.length && !logSeleccionado.navegador && !logSeleccionado.so" class="modal-vacio">Sin información adicional registrada.</p>

          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

.page { display: flex; flex-direction: column; height: 100%; overflow: hidden; padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; }
.page-header { flex-shrink: 0; margin-bottom: 1.5rem; }
.page-title    { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

/* Filtros */
.filtros-card {
  flex-shrink: 0;
  background: #fff; border: 1px solid #E5E7EB; border-radius: 14px;
  padding: 1.25rem; margin-bottom: 1.25rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.filtros-grid {
  display: flex; flex-wrap: wrap; gap: 0.875rem; align-items: flex-end;
}
.filtro-item { display: flex; flex-direction: column; min-width: 160px; }
.filtro-buscar { flex: 1; min-width: 220px; }
.filtro-btns { display: flex; gap: 0.5rem; align-items: flex-end; padding-top: 0.1rem; }

.label-filtro {
  display: block; font-size: 0.6875rem; font-weight: 600;
  color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.06em;
  margin-bottom: 0.35rem;
}

.input-icon-wrap { position: relative; }
.input-icon-wrap svg { position: absolute; left: 0.625rem; top: 50%; transform: translateY(-50%); width: 15px; height: 15px; color: #9CA3AF; pointer-events: none; }
.input-icon-wrap .filter-input { padding-left: 2rem; }

.filter-input {
  width: 100%; padding: 0.5rem 0.75rem;
  border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: 0.875rem; color: #374151; background: #F9FAFB;
  outline: none; font-family: inherit;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
}
.filter-input:focus { background: #fff; border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }

.btn-primary {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 1.1rem; background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; font-size: 0.875rem; font-weight: 600;
  border: none; border-radius: 8px; cursor: pointer; font-family: inherit;
  transition: opacity 0.15s; white-space: nowrap;
}
.btn-primary svg { width: 14px; height: 14px; }
.btn-primary:hover { opacity: 0.88; }

.btn-ghost {
  padding: 0.5rem 0.875rem; font-size: 0.875rem; font-weight: 500;
  color: #6B7280; background: transparent; border: 1px solid #E5E7EB;
  border-radius: 8px; cursor: pointer; font-family: inherit;
  transition: color 0.15s, border-color 0.15s; white-space: nowrap;
}
.btn-ghost:hover { color: #4F46E5; border-color: #C4B5FD; }

/* Loading */
.loading { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }
.spinner { width: 22px; height: 22px; border: 2.5px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Tabla */
.tabla-card { flex: 1; min-height: 0; display: flex; flex-direction: column; background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.tabla-scroll { flex: 1; min-height: 0; overflow: auto; }
.tabla { width: 100%; border-collapse: collapse; }
.tabla thead { position: sticky; top: 0; z-index: 10; border-bottom: 2px solid #E5E7EB; }
.tabla th { padding: 0.75rem 1rem; text-align: left; font-size: 0.6875rem; font-weight: 700; color: #6B7280; text-transform: uppercase; letter-spacing: 0.06em; background: #F9FAFB; }
.tabla td { padding: 0.8rem 1rem; font-size: 0.875rem; color: #374151; border-bottom: 1px solid #F3F4F6; vertical-align: middle; }
.tabla tr:last-child td { border-bottom: none; }
.tabla tbody tr { transition: background 0.1s; }
.tabla tbody tr:hover td { background: #FAFAFA; }

.td-fecha  { font-variant-numeric: tabular-nums; white-space: nowrap; color: #6B7280; font-size: 0.8125rem; }
.td-mono   { font-family: 'Courier New', monospace; font-size: 0.78rem; color: #6B7280; }

/* Usuario en tabla: nombre arriba, email debajo */
.td-usuario { font-size: 0.8125rem; line-height: 1.3; }
.usr-nombre { display: block; font-weight: 600; color: #111827; }
.usr-email  { display: block; font-size: 0.75rem; color: #9CA3AF; }

/* Usuario en chip del modal: nombre + email en gris */
.chip-usuario { flex-direction: column; align-items: flex-start; gap: 0.05rem; padding: 0.3rem 0.6rem; }
.chip-email   { font-size: 0.68rem; color: #9CA3AF; font-weight: 400; }
.td-sin-detalle { color: #D1D5DB; font-size: 0.875rem; }
.empty-row { text-align: center; color: #9CA3AF; padding: 3rem !important; font-size: 0.875rem; }

/* Botón detalle */
.btn-detalle {
  width: 30px; height: 30px; border-radius: 8px;
  border: 1px solid #E5E7EB; background: #F9FAFB;
  display: inline-flex; align-items: center; justify-content: center;
  cursor: pointer; color: #6B7280;
  transition: all 0.15s;
}
.btn-detalle svg { width: 15px; height: 15px; }
.btn-detalle:hover { border-color: #7C3AED; background: #F5F3FF; color: #7C3AED; }
.btn-detalle--activo { border-color: #7C3AED; background: #EDE9FE; color: #7C3AED; }

/* Badges */
.badge {
  display: inline-flex; align-items: center;
  padding: 0.22rem 0.6rem; border-radius: 999px;
  font-size: 0.7rem; font-weight: 700; white-space: nowrap;
}
.badge-seguridad { background: #EDE9FE; color: #5B21B6; }
.badge-actividad { background: #EFF6FF; color: #1D4ED8; }
.badge-verde    { background: #ECFDF5; color: #059669; }
.badge-rojo     { background: #FEF2F2; color: #DC2626; }
.badge-naranja  { background: #FFFBEB; color: #D97706; }
.badge-morado   { background: #F5F3FF; color: #7C3AED; }
.badge-azul     { background: #EFF6FF; color: #2563EB; }
.badge-amarillo { background: #FEFCE8; color: #CA8A04; }
.badge-gris     { background: #F3F4F6; color: #6B7280; }

/* Paginación */
.paginacion { flex-shrink: 0; display: flex; align-items: center; justify-content: center; gap: 0.3rem; margin-top: 1.5rem; }
.pag-btn {
  width: 34px; height: 34px; border: 1px solid #E5E7EB; border-radius: 8px;
  background: #fff; display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: #6B7280; transition: all 0.15s;
}
.pag-btn:hover:not(:disabled) { border-color: #4F46E5; color: #4F46E5; }
.pag-btn:disabled { opacity: 0.35; cursor: default; }
.pag-btn svg { width: 14px; height: 14px; }
.pag-num {
  width: 34px; height: 34px; border: 1px solid #E5E7EB; border-radius: 8px;
  background: #fff; font-size: 0.875rem; color: #374151;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.pag-num:hover  { border-color: #4F46E5; color: #4F46E5; }
.pag-num.active { background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; border-color: transparent; font-weight: 700; }
.pag-dots { color: #9CA3AF; font-size: 0.875rem; padding: 0 0.1rem; line-height: 34px; }

/* ── Modal de detalles ───────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; z-index: 50;
  background: rgba(15,15,35,0.45); backdrop-filter: blur(3px);
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
  animation: overlayIn 0.15s ease;
}
@keyframes overlayIn { from { opacity: 0 } to { opacity: 1 } }

.modal-box {
  background: #fff; border-radius: 16px;
  width: 100%; max-width: 480px;
  max-height: 80vh;
  display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.08);
  animation: modalIn 0.18s ease;
  overflow: hidden;
}
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95) translateY(8px) }
  to   { opacity: 1; transform: scale(1)    translateY(0)   }
}

/* Header */
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #F3F4F6;
  flex-shrink: 0;
}
.modal-header-info { display: flex; align-items: center; gap: 0.75rem; }
.modal-fecha { font-size: 0.78rem; color: #9CA3AF; }
.modal-cerrar {
  width: 28px; height: 28px; border: 1px solid #E5E7EB; border-radius: 7px;
  background: #F9FAFB; cursor: pointer; color: #9CA3AF;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: all 0.13s;
}
.modal-cerrar:hover { background: #FEF2F2; border-color: #FECACA; color: #DC2626; }
.modal-cerrar svg { width: 14px; height: 14px; }

/* Body */
.modal-body {
  padding: 1rem 1.25rem 1.25rem;
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 0.875rem;
}

/* Chips de contexto (tipo, usuario, IP, navegador) */
.modal-chips {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem;
}
.chip-info {
  display: inline-flex; align-items: center; gap: 0.3rem;
  padding: 0.2rem 0.6rem; border-radius: 999px;
  background: #F3F4F6; color: #374151;
  font-size: 0.75rem; font-weight: 500;
}
.chip-mono { font-family: 'Courier New', monospace; font-size: 0.72rem; }

/* Descripción legible */
.modal-descripcion {
  font-size: 0.875rem; color: #374151; font-weight: 500;
  background: #F5F3FF; border-left: 3px solid #7C3AED;
  border-radius: 0 8px 8px 0; padding: 0.6rem 0.875rem;
  margin: 0; line-height: 1.5;
}

/* SO chip */
.chip-so { background: #F0FDF4; color: #15803D; }

/* Endpoint HTTP */
.modal-endpoint {
  display: flex; align-items: center; gap: 0.5rem;
  background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;
  padding: 0.45rem 0.75rem; font-size: 0.75rem;
}
.endpoint-metodo {
  background: #1E40AF; color: #fff;
  padding: 0.1rem 0.45rem; border-radius: 4px;
  font-weight: 700; font-size: 0.68rem; letter-spacing: 0.04em; flex-shrink: 0;
}
.endpoint-path {
  font-family: 'Courier New', monospace; color: #475569;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* User-Agent */
.modal-ua {
  font-size: 0.7rem; color: #B0B7C3;
  font-family: 'Courier New', monospace;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin: 0; cursor: help;
}

/* Tabla antes/después */
.modal-cambios {
  border: 1px solid #E5E7EB; border-radius: 10px; overflow: hidden;
  font-size: 0.8rem;
}
.cambios-header {
  display: grid; grid-template-columns: 1fr 1fr 1fr;
  background: #F9FAFB; padding: 0.45rem 0.75rem;
  border-bottom: 1px solid #E5E7EB;
  font-size: 0.65rem; font-weight: 700; color: #9CA3AF;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.cambio-fila {
  display: grid; grid-template-columns: 1fr 1fr 1fr;
  padding: 0.55rem 0.75rem; border-bottom: 1px solid #F3F4F6;
  align-items: center; gap: 0.5rem;
}
.cambio-fila:last-child { border-bottom: none; }
.cambio-fila:nth-child(even) { background: #FAFAFA; }
.cambio-campo  { font-weight: 600; color: #6B7280; }
.cambio-antes  { color: #DC2626; text-decoration: line-through; word-break: break-word; }
.cambio-despues { color: #059669; font-weight: 600; word-break: break-word; }

/* Tabla de datos */
.modal-section-title {
  font-size: 0.65rem; font-weight: 700; color: #9CA3AF;
  text-transform: uppercase; letter-spacing: 0.07em; margin: 0;
}
.modal-filas {
  border: 1px solid #E5E7EB; border-radius: 10px; overflow: hidden;
}
.modal-fila {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.6rem 0.875rem; gap: 1rem;
  border-bottom: 1px solid #F3F4F6;
}
.modal-fila:last-child { border-bottom: none; }
.modal-fila:nth-child(even) { background: #FAFAFA; }
.modal-clave { font-size: 0.8rem; font-weight: 600; color: #6B7280; flex-shrink: 0; }
.modal-valor { font-size: 0.8125rem; color: #111827; text-align: right; word-break: break-word; }
.modal-vacio { font-size: 0.875rem; color: #9CA3AF; text-align: center; margin: 0.5rem 0; }
.drag-handle { display: none; }

/* Navegador (badges en tabla y chips) */
.td-navegador { vertical-align: middle; }
.badge-navegador {
  display: inline-flex; align-items: center;
  padding: 0.18rem 0.55rem; border-radius: 999px;
  font-size: 0.68rem; font-weight: 700; white-space: nowrap;
}
.nav-chrome            { background: #FEF9C3; color: #854D0E; }
.nav-firefox           { background: #FFF7ED; color: #C2410C; }
.nav-edge              { background: #EFF6FF; color: #1D4ED8; }
.nav-safari            { background: #F0FDF4; color: #15803D; }
.nav-opera             { background: #FEF2F2; color: #B91C1C; }
.nav-brave             { background: #FFF1F2; color: #BE123C; }
.nav-arc               { background: #F5F3FF; color: #6D28D9; }
.nav-vivaldi           { background: #FDF4FF; color: #86198F; }
.nav-samsung_internet  { background: #ECFDF5; color: #065F46; }
.nav-app_móvil         { background: #F0F9FF; color: #0369A1; }
.nav-internet_explorer { background: #F1F5F9; color: #475569; }
.nav-otro              { background: #F3F4F6; color: #6B7280; }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .page-title { font-size: 1.25rem; }

  /* Filtros en columna */
  .filtros-card { padding: 1rem; }
  .filtros-grid { gap: 0.625rem; }
  .filtro-item, .filtro-buscar { min-width: 100%; }
  .filtro-btns { width: 100%; }
  .filtro-btns .btn-primary,
  .filtro-btns .btn-ghost { flex: 1; justify-content: center; }

  /* Fecha más compacta */
  .tabla th:nth-child(1) { width: 90px; }
  .td-fecha { font-size: 0.75rem; white-space: normal; line-height: 1.3; }

  /* Acción: badge más pequeño */
  .badge { font-size: 0.65rem; padding: 0.18rem 0.45rem; }

  /* Usuario: solo nombre en mobile */
  .usr-email { display: none; }

  /* Botón detalle compacto */
  .tabla th:last-child { width: 44px; }

  /* Modal desliza desde abajo */
  .modal-overlay { padding: 0; align-items: flex-end; }
  .modal-box { max-width: 100%; max-height: 90vh; border-radius: 16px 16px 0 0; padding-top: 0.75rem; }
  .drag-handle {
    display: block;
    width: 40px;
    height: 4px;
    border-radius: 999px;
    background: #E5E7EB;
    margin: 0 auto 0.5rem;
    flex-shrink: 0;
  }
  .cambios-header,
  .cambio-fila { grid-template-columns: 0.8fr 1fr 1fr; font-size: 0.75rem; }
  /* Scroll del contenedor de tabla con thumb visible */
  .tabla-scroll {
    scrollbar-width: thin;
    scrollbar-color: #A78BFA #EDE9FE;
  }
  .tabla-scroll::-webkit-scrollbar { height: 8px; width: 8px; }
  .tabla-scroll::-webkit-scrollbar-track { background: #EDE9FE; border-radius: 999px; }
  .tabla-scroll::-webkit-scrollbar-thumb { background: #7C3AED; border-radius: 999px; min-width: 40px; }
  .tabla-scroll::-webkit-scrollbar-thumb:hover { background: #6D28D9; }
  .tabla-scroll .tabla { min-width: 520px; }

}
</style>
