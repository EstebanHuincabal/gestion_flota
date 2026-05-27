<template>
  <div class="min-h-screen bg-gray-50">
    <div class="p-6 max-w-screen-xl mx-auto">

      <!-- ── Header ── -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Rutas y trabajos</h1>
          <p class="text-sm text-gray-500 mt-0.5">Planificación y seguimiento de rutas vehiculares</p>
        </div>
        <button @click="abrirModalCrear"
          :disabled="esSuperadmin && !empresaActiva"
          :title="esSuperadmin && !empresaActiva ? 'Selecciona una empresa primero' : ''"
          class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Nueva ruta
        </button>
      </div>

      <!-- ── Selector empresa (solo SUPERADMIN) ── -->
      <div v-if="esSuperadmin" class="relative mb-5">
        <button
          @click="mostrarDropdownEmpresa = !mostrarDropdownEmpresa"
          :class="['flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition',
            empresaActiva ? 'bg-white border-gray-200 text-gray-700' : 'bg-amber-50 border-amber-300 text-amber-700']"
        >
          <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
          </svg>
          <span class="font-medium">{{ empresaActiva ? empresaActiva.nombre : 'Seleccionar empresa' }}</span>
          <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>

        <div v-if="mostrarDropdownEmpresa"
          class="absolute top-full left-0 mt-1 w-72 bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden">
          <div class="p-2 border-b border-gray-100">
            <input v-model="busquedaEmpresa" placeholder="Buscar empresa..."
              class="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-indigo-500"
              autofocus/>
          </div>
          <div class="max-h-60 overflow-y-auto">
            <div v-if="!empresasFiltradas.length" class="px-4 py-3 text-sm text-gray-400 text-center">Sin resultados</div>
            <button v-for="emp in empresasFiltradas" :key="emp.id"
              @click="seleccionarEmpresa(emp)"
              :class="['w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left hover:bg-gray-50 transition',
                empresaActiva?.id === emp.id ? 'text-indigo-600 font-semibold' : 'text-gray-700']"
            >
              <span class="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
                {{ emp.nombre[0].toUpperCase() }}
              </span>
              {{ emp.nombre }}
              <svg v-if="empresaActiva?.id === emp.id" class="w-4 h-4 ml-auto text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- ── Sin empresa seleccionada (SUPERADMIN) ── -->
      <div v-if="sinEmpresa" class="bg-white rounded-xl border border-amber-200 p-12 text-center">
        <svg class="w-12 h-12 mx-auto mb-3 text-amber-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
        </svg>
        <p class="text-gray-500 text-sm">Selecciona una empresa para ver sus rutas</p>
      </div>

      <!-- ── KPI Cards ── -->
      <div v-if="!sinEmpresa" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs text-gray-500 mb-1">Rutas activas</p>
          <p class="text-2xl font-bold text-green-600">{{ resumen.activas }}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs text-gray-500 mb-1">Pendientes hoy</p>
          <p class="text-2xl font-bold text-blue-600">{{ resumen.pendientes }}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs text-gray-500 mb-1">Km este mes</p>
          <p class="text-2xl font-bold text-indigo-600">{{ resumen.km_mes.toLocaleString('es-CL') }}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs text-gray-500 mb-1">Finalizadas este mes</p>
          <p class="text-2xl font-bold text-gray-800">{{ resumen.finalizadas_mes || 0 }}</p>
        </div>
      </div>

      <!-- ── Tabs ── -->
      <div v-if="!sinEmpresa" class="flex gap-1 mb-4 bg-white border border-gray-200 rounded-lg p-1 w-fit">
        <button v-for="tab in tabs" :key="tab.key"
          @click="tabActivo = tab.key"
          :class="['px-4 py-1.5 text-sm rounded-md transition font-medium',
            tabActivo === tab.key ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-100']">
          {{ tab.label }}
        </button>
      </div>

      <!-- ── Tabla ── -->
      <div v-if="!sinEmpresa" class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div v-if="cargando" class="flex justify-center py-16">
          <div class="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        </div>

        <div v-else-if="rutasFiltradas.length === 0" class="text-center py-16 text-gray-400">
          <svg class="w-12 h-12 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
          </svg>
          <p class="text-sm">No hay rutas en esta categoría</p>
        </div>

        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
              <th class="px-4 py-3 text-left font-semibold">Nombre / Ruta</th>
              <th class="px-4 py-3 text-left font-semibold">Tipo</th>
              <th class="px-4 py-3 text-left font-semibold">Conductor</th>
              <th class="px-4 py-3 text-left font-semibold">Vehículo</th>
              <th class="px-4 py-3 text-left font-semibold">Fecha</th>
              <th class="px-4 py-3 text-right font-semibold">Distancia / Duración</th>
              <th class="px-4 py-3 text-center font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="ruta in rutasFiltradas" :key="ruta.id"
              @click="abrirPanel(ruta)"
              class="hover:bg-indigo-50/30 cursor-pointer transition group">
              <td class="px-4 py-3">
                <p class="font-medium text-gray-900 group-hover:text-indigo-700">{{ ruta.nombre }}</p>
                <p class="text-xs text-gray-400">
                  {{ ruta.origen || '—' }}
                  <span v-if="ruta.destino"> → {{ ruta.destino }}</span>
                </p>
              </td>
              <td class="px-4 py-3">
                <span :class="['px-2 py-0.5 rounded-full text-xs font-medium',
                  ruta.tipo === 'carga' ? 'bg-amber-100 text-amber-700' : 'bg-purple-100 text-purple-700']">
                  {{ ruta.tipo === 'carga' ? 'Carga' : 'Personas' }}
                </span>
              </td>
              <td class="px-4 py-3 text-gray-600">{{ ruta.conductor || '—' }}</td>
              <td class="px-4 py-3 text-gray-600">{{ ruta.vehiculo || '—' }}</td>
              <td class="px-4 py-3 text-gray-500">
                {{ ruta.fecha_programada ? formatFecha(ruta.fecha_programada) : '—' }}
                <span v-if="ruta.hora_programada" class="ml-1 text-xs font-semibold text-indigo-500">{{ ruta.hora_programada }}</span>
              </td>
              <td class="px-4 py-3 text-right">
                <p class="font-medium text-gray-800">{{ ruta.distancia_km ? ruta.distancia_km.toLocaleString('es-CL') + ' km' : '—' }}</p>
                <p class="text-xs text-gray-400">{{ ruta.duracion_min ? formatDuracion(ruta.duracion_min) : '' }}</p>
              </td>
              <td class="px-4 py-3 text-center" @click.stop>
                <span :class="['px-2.5 py-1 rounded-full text-xs font-semibold', badgeEstado(ruta.estado)]">
                  <span v-if="ruta.estado === 'activo'" class="inline-block w-1.5 h-1.5 rounded-full bg-current mr-1 animate-pulse"></span>
                  {{ labelEstado(ruta.estado) }}
                </span>
              </td>
              <td class="px-4 py-3 text-center" @click.stop>
                <div class="flex items-center justify-center gap-1">
                  <template v-if="ruta.estado === 'pendiente'">
                    <button @click="prepararIniciar(ruta)" title="Iniciar"
                      class="p-1.5 text-green-600 hover:bg-green-50 rounded-lg transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                    </button>
                    <button @click="abrirModalEditar(ruta)" title="Editar"
                      class="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-lg transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                      </svg>
                    </button>
                    <button @click="prepararCancelar(ruta)" title="Cancelar"
                      class="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </template>
                  <template v-else-if="ruta.estado === 'activo'">
                    <button @click="prepararFinalizar(ruta)" title="Finalizar"
                      class="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                    </button>
                    <button @click="prepararCancelar(ruta)" title="Cancelar"
                      class="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </template>
                  <button @click="abrirPanel(ruta)" title="Ver detalle"
                    class="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg transition">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Panel lateral ── -->
    <Transition name="panel">
      <div v-if="panelAbierto" class="fixed inset-0 z-30 flex justify-end">
        <div class="absolute inset-0 bg-black/20" @click="panelAbierto = false"></div>
        <div class="relative bg-white w-full max-w-2xl shadow-2xl flex flex-col overflow-hidden">
          <!-- Header panel -->
          <div class="flex items-start justify-between p-5 border-b border-gray-100">
            <div>
              <h2 class="text-lg font-bold text-gray-900">{{ rutaDetalle?.nombre }}</h2>
              <p class="text-sm text-gray-400 mt-0.5">
                {{ rutaDetalle?.origen }}
                <span v-if="rutaDetalle?.destino"> → {{ rutaDetalle.destino }}</span>
              </p>
            </div>
            <button @click="panelAbierto = false" class="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Tabs del panel -->
          <div class="flex border-b border-gray-100 px-5">
            <button v-for="t in ['detalle','mapa','historial']" :key="t"
              @click="cambiarTabPanel(t)"
              :class="['py-3 mr-5 text-sm font-medium border-b-2 transition capitalize',
                tabPanel === t ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-gray-500 hover:text-gray-700']">
              {{ t }}
            </button>
          </div>

          <!-- Contenido panel -->
          <div class="flex-1 overflow-y-auto p-5">

            <!-- Tab Detalle -->
            <div v-if="tabPanel === 'detalle'" class="space-y-4">
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Estado</p>
                  <span :class="['px-2.5 py-0.5 rounded-full text-xs font-semibold', badgeEstado(rutaDetalle?.estado)]">
                    {{ labelEstado(rutaDetalle?.estado) }}
                  </span>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Tipo</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle?.tipo === 'carga' ? 'Carga' : 'Personas' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Conductor</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle?.conductor || '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Vehículo</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle?.vehiculo || '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Fecha programada</p>
                  <p class="font-medium text-gray-800">
                    {{ rutaDetalle?.fecha_programada ? formatFecha(rutaDetalle.fecha_programada) : '—' }}
                    <span v-if="rutaDetalle?.hora_programada" class="ml-1 text-indigo-600 font-semibold">
                      {{ rutaDetalle.hora_programada }}
                    </span>
                  </p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Distancia</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle?.distancia_km ? rutaDetalle.distancia_km.toLocaleString('es-CL') + ' km' : '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Duración estimada</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle?.duracion_min ? formatDuracion(rutaDetalle.duracion_min) : '—' }}</p>
                </div>
                <div v-if="rutaDetalle?.km_reales">
                  <p class="text-xs text-gray-400 mb-0.5">Km recorridos</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle.km_reales.toLocaleString('es-CL') }} km</p>
                </div>
              </div>

              <!-- Paradas -->
              <div v-if="rutaDetalle?.paradas?.length" class="mt-4">
                <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Paradas</p>
                <ol class="relative border-l-2 border-gray-200 ml-2 space-y-3">
                  <li v-for="p in rutaDetalle.paradas" :key="p.id" class="ml-4">
                    <div :class="['absolute w-3 h-3 rounded-full -left-1.5 border-2 border-white',
                      p.tipo === 'origen' ? 'bg-green-500' : p.tipo === 'destino' ? 'bg-red-500' : 'bg-blue-400']"></div>
                    <p class="text-sm font-medium text-gray-800">{{ p.nombre }}</p>
                    <p class="text-xs text-gray-400">{{ p.direccion || p.tipo }}</p>
                  </li>
                </ol>
              </div>

            </div>

            <!-- Tab Mapa -->
            <div v-if="tabPanel === 'mapa'" style="height:420px">
              <MapaRuta
                map-id="panel-mapa"
                :paradas="rutaDetalle?.paradas || []"
                :polyline="rutaDetalle?.polyline || []"
              />
            </div>

            <!-- Tab Historial -->
            <div v-if="tabPanel === 'historial'" class="flex flex-col h-full">
              <!-- Lista de eventos -->
              <div v-if="cargandoEventos" class="flex justify-center py-8">
                <div class="w-6 h-6 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
              </div>

              <div v-else class="flex-1 space-y-3 mb-4">
                <div v-if="!eventos.length" class="text-center py-8 text-gray-400 text-sm">
                  No hay eventos aún.
                </div>
                <div v-for="e in eventos" :key="e.id"
                  class="flex gap-3 items-start">
                  <!-- Icono -->
                  <div :class="['flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white',
                    e.tipo === 'auto' ? 'bg-indigo-500' : 'bg-green-500']">
                    <!-- auto: engranaje -->
                    <svg v-if="e.tipo === 'auto'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    </svg>
                    <!-- comentario: burbuja -->
                    <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                    </svg>
                  </div>
                  <!-- Contenido -->
                  <div class="flex-1 min-w-0">
                    <p class="text-sm text-gray-800">{{ e.texto }}</p>
                    <p class="text-xs text-gray-400 mt-0.5">
                      {{ e.autor || 'Sistema' }} · {{ formatTimestamp(e.created_at) }}
                    </p>
                  </div>
                </div>
              </div>

              <!-- Input nuevo comentario -->
              <div class="border-t border-gray-100 pt-4">
                <div class="flex gap-2">
                  <input v-model="nuevoComentario" type="text" placeholder="Agregar comentario..."
                    class="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                    @keydown.enter="enviarComentario"/>
                  <button @click="enviarComentario" :disabled="!nuevoComentario.trim() || enviandoComentario"
                    class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50">
                    Enviar
                  </button>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Modal crear / editar (3 pasos) ── -->
    <Transition name="modal">
      <div v-if="modalCrear" class="fixed inset-0 z-40 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40" @click="cerrarModal"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">

          <!-- Header modal -->
          <div class="flex items-center justify-between p-5 border-b border-gray-100">
            <div>
              <h3 class="text-lg font-bold text-gray-900">{{ modoEdicion ? 'Editar ruta' : 'Nueva ruta' }}</h3>
              <p class="text-xs text-gray-400 mt-0.5">Paso {{ paso }} de 3</p>
            </div>
            <button @click="cerrarModal" class="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Indicador de pasos -->
          <div class="flex px-5 pt-4 gap-2">
            <div v-for="n in 3" :key="n"
              :class="['h-1 flex-1 rounded-full transition-all', n <= paso ? 'bg-indigo-600' : 'bg-gray-200']"></div>
          </div>

          <!-- Contenido del paso -->
          <div class="flex-1 overflow-y-auto p-5">

            <!-- Paso 1 — Datos generales -->
            <div v-if="paso === 1" class="space-y-4">
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-2">Tipo de ruta</label>
                <div class="grid grid-cols-2 gap-3">
                  <label v-for="opt in [{v:'carga',l:'Carga'},{v:'personas',l:'Personas'}]" :key="opt.v"
                    :class="['flex items-center gap-2.5 p-3 border-2 rounded-xl cursor-pointer transition',
                      form.tipo === opt.v ? 'border-indigo-600 bg-indigo-50' : 'border-gray-200 hover:border-gray-300']">
                    <input type="radio" :value="opt.v" v-model="form.tipo" class="sr-only">
                    <span class="text-sm font-medium text-gray-800">{{ opt.l }}</span>
                  </label>
                </div>
              </div>
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">Nombre de la ruta *</label>
                <input v-model="form.nombre" type="text" placeholder="Ej: Santiago → Valparaíso"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1">Conductor</label>
                  <select v-model="form.conductor_id" @change="onConductorChange"
                    :class="['w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition',
                      autoFillConductor ? 'border-indigo-400 bg-indigo-50' : 'border-gray-200']">
                    <option :value="null">Sin asignar</option>
                    <option v-for="c in conductores" :key="c.id" :value="c.id">{{ c.nombre }}</option>
                  </select>
                  <p v-if="autoFillConductor" class="mt-1 text-xs text-indigo-600 flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    Autocompletado por vehículo asignado
                  </p>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1">Vehículo</label>
                  <select v-model="form.vehiculo_id" @change="onVehiculoChange"
                    :class="['w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition',
                      autoFillVehiculo ? 'border-indigo-400 bg-indigo-50' : 'border-gray-200']">
                    <option :value="null">Sin asignar</option>
                    <option v-for="v in vehiculos" :key="v.id" :value="v.id">{{ v.patente }} — {{ v.marca }} {{ v.modelo }}</option>
                  </select>
                  <p v-if="autoFillVehiculo" class="mt-1 text-xs text-indigo-600 flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    Autocompletado por conductor asignado
                  </p>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1">Fecha programada</label>
                  <input v-model="form.fecha_programada" type="date"
                    @change="validacionResult = null; advertenciasAceptadas = false"
                    class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1">
                    Hora programada
                    <span class="text-gray-400 font-normal">(opcional)</span>
                  </label>
                  <input v-model="form.hora_programada" type="time"
                    @change="validacionResult = null; advertenciasAceptadas = false"
                    class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                </div>
              </div>
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">Notas</label>
                <textarea v-model="form.notas" rows="2" placeholder="Instrucciones, observaciones..."
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"></textarea>
              </div>

              <!-- ── Panel de validación pre-vuelo ─────────────────────── -->
              <transition name="fade-slide">
              <div v-if="validacionResult" class="mt-1">

                <!-- Errores bloqueantes -->
                <div v-if="validacionResult.errores?.length"
                  class="rounded-xl border border-red-300 bg-red-50 overflow-hidden">
                  <div class="flex items-center gap-2.5 px-4 py-3 bg-red-100 border-b border-red-200">
                    <div class="w-7 h-7 rounded-full bg-red-500 flex items-center justify-center shrink-0">
                      <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </div>
                    <p class="text-sm font-bold text-red-800">No se puede programar esta ruta</p>
                  </div>
                  <ul class="px-4 py-3 space-y-2">
                    <li v-for="e in validacionResult.errores" :key="e.codigo"
                      class="flex items-start gap-2 text-sm text-red-700">
                      <svg class="w-4 h-4 text-red-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd"/>
                      </svg>
                      <span>{{ e.mensaje }}</span>
                    </li>
                  </ul>
                </div>

                <!-- Advertencias (solo si no hay errores) -->
                <div v-if="validacionResult.advertencias?.length && !validacionResult.errores?.length"
                  class="rounded-xl border overflow-hidden"
                  :class="advertenciasAceptadas ? 'border-green-300 bg-green-50' : 'border-amber-300 bg-amber-50'">

                  <!-- Header -->
                  <div class="flex items-center gap-2.5 px-4 py-3 border-b"
                    :class="advertenciasAceptadas ? 'bg-green-100 border-green-200' : 'bg-amber-100 border-amber-200'">
                    <div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                      :class="advertenciasAceptadas ? 'bg-green-500' : 'bg-amber-400'">
                      <svg v-if="advertenciasAceptadas" class="w-4 h-4 text-white" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                      </svg>
                      <svg v-else class="w-4 h-4 text-white" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                      </svg>
                    </div>
                    <p class="text-sm font-bold"
                      :class="advertenciasAceptadas ? 'text-green-800' : 'text-amber-800'">
                      {{ advertenciasAceptadas ? 'Confirmado — puedes continuar' : `${validacionResult.advertencias.length} advertencia${validacionResult.advertencias.length > 1 ? 's' : ''} detectada${validacionResult.advertencias.length > 1 ? 's' : ''}` }}
                    </p>
                  </div>

                  <!-- Lista de advertencias -->
                  <ul class="px-4 py-3 space-y-2">
                    <li v-for="a in validacionResult.advertencias" :key="a.codigo"
                      class="flex items-start gap-2 text-sm"
                      :class="advertenciasAceptadas ? 'text-green-700' : 'text-amber-700'">
                      <svg class="w-4 h-4 shrink-0 mt-0.5" :class="advertenciasAceptadas ? 'text-green-400' : 'text-amber-400'" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/>
                      </svg>
                      <span>{{ a.mensaje }}</span>
                    </li>
                  </ul>

                  <!-- Botón "Programar de todas formas" -->
                  <div v-if="!advertenciasAceptadas" class="px-4 pb-4">
                    <button
                      @click="advertenciasAceptadas = true"
                      class="w-full py-2.5 text-sm font-semibold text-white bg-amber-500 hover:bg-amber-600 rounded-lg transition flex items-center justify-center gap-2">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                      </svg>
                      Programar de todas formas
                    </button>
                  </div>
                </div>

              </div>
              </transition>
            </div>

            <!-- Paso 2 — Paradas -->
            <div v-if="paso === 2" class="space-y-3">
              <p class="text-xs text-gray-500 mb-1">Ingresa el origen, destino y las paradas intermedias.</p>

              <div v-for="(parada, idx) in form.paradas" :key="idx"
                class="border border-gray-200 rounded-xl p-3 relative">
                <div class="flex items-center justify-between mb-2">
                  <span :class="['text-xs font-semibold px-2 py-0.5 rounded-full',
                    parada.tipo === 'origen' ? 'bg-green-100 text-green-700' :
                    parada.tipo === 'destino' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700']">
                    {{ parada.tipo === 'origen' ? 'Origen' : parada.tipo === 'destino' ? 'Destino' : `Parada ${idx}` }}
                  </span>
                  <button v-if="parada.tipo === 'parada'" @click="quitarParada(idx)"
                    class="p-1 text-red-400 hover:bg-red-50 rounded-lg transition">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
                <div class="relative">
                  <input :value="parada.nombre || parada.direccion"
                    @input="e => buscarDireccion(e.target.value, idx)"
                    type="text" :placeholder="parada.tipo === 'origen' ? 'Buscar dirección de origen...' : parada.tipo === 'destino' ? 'Buscar dirección de destino...' : 'Buscar parada...'"
                    class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                  <div v-if="geoSugerencias[idx]?.length"
                    class="absolute top-full mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto">
                    <button v-for="(sug, si) in geoSugerencias[idx]" :key="si"
                      @click="seleccionarDireccion(sug, idx)"
                      class="w-full text-left px-3 py-2 text-xs text-gray-700 hover:bg-indigo-50 border-b border-gray-50 last:border-0">
                      {{ sug.display_name }}
                    </button>
                  </div>
                </div>
                <div v-if="parada.latitud" class="mt-1 text-xs text-green-600">
                  ✓ {{ parada.latitud.toFixed(4) }}, {{ parada.longitud.toFixed(4) }}
                </div>
              </div>

              <button @click="agregarParada"
                class="w-full border-2 border-dashed border-gray-200 text-gray-400 rounded-xl py-2.5 text-sm hover:border-indigo-300 hover:text-indigo-500 transition">
                + Agregar parada intermedia
              </button>
            </div>

            <!-- Paso 3 — Calcular y confirmar -->
            <div v-if="paso === 3" class="space-y-4">
              <div v-if="calculando" class="flex flex-col items-center justify-center py-10 gap-3 text-gray-400">
                <div class="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                <p class="text-sm">Calculando ruta con OSRM...</p>
              </div>

              <div v-else-if="calculoResult">
                <!-- Mapa del cálculo -->
                <div style="height:250px" class="rounded-xl overflow-hidden border border-gray-200 mb-3">
                  <MapaRuta
                    map-id="calc-mapa"
                    :paradas="form.paradas.filter(p => p.latitud)"
                    :polyline="calculoResult.polyline || []"
                  />
                </div>

                <!-- Alerta OSRM falla -->
                <div v-if="calculoResult.aviso" class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700 mb-3">
                  ⚠️ {{ calculoResult.aviso }}
                </div>

                <!-- Datos calculados -->
                <div class="grid grid-cols-2 gap-3">
                  <div class="bg-gray-50 rounded-lg p-3 text-sm">
                    <p class="text-xs text-gray-400">Distancia</p>
                    <p class="font-bold text-gray-800">{{ calculoResult.distancia_km ? calculoResult.distancia_km.toLocaleString('es-CL') + ' km' : '—' }}</p>
                  </div>
                  <div class="bg-gray-50 rounded-lg p-3 text-sm">
                    <p class="text-xs text-gray-400">Duración estimada</p>
                    <p class="font-bold text-gray-800">{{ calculoResult.duracion_min ? formatDuracion(calculoResult.duracion_min) : '—' }}</p>
                  </div>
                </div>
              </div>

              <div v-else class="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-700">
                No se pudo conectar con el servicio de rutas. Puede crear la ruta de todas formas sin datos de distancia.
              </div>
            </div>
          </div>

          <!-- Footer modal -->
          <div class="border-t border-gray-100">
            <div v-if="errorModal"
                 class="flex items-start gap-2 px-4 py-3 bg-red-50 border-b border-red-100">
              <svg class="w-4 h-4 text-red-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
              <p class="text-xs text-red-700 whitespace-pre-line leading-relaxed">{{ errorModal }}</p>
            </div>

            <div class="flex items-center justify-between p-4">
              <button v-if="paso > 1" @click="paso--; errorModal = ''"
                class="px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition">
                Anterior
              </button>
              <div v-else></div>
              <div class="flex gap-2">
                <button @click="cerrarModal" class="px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg transition">
                  Cancelar
                </button>
                <button v-if="paso < 3" @click="siguientePaso"
                  :disabled="(paso === 1 && !form.nombre.trim()) || validando || (validacionResult?.errores?.length > 0)"
                  class="px-5 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5">
                  <svg v-if="validando" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  {{ validando ? 'Verificando...' : 'Siguiente' }}
                </button>
                <button v-else @click="guardarRuta" :disabled="guardando"
                  class="px-5 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50">
                  {{ guardando ? 'Guardando...' : (modoEdicion ? 'Guardar cambios' : 'Crear ruta') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Modal Finalizar ── -->
    <Transition name="modal">
      <div v-if="modalFinalizar" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40" @click="modalFinalizar = false"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
          <h3 class="text-lg font-bold text-gray-900 mb-1">Finalizar ruta</h3>
          <p class="text-sm text-gray-500 mb-4">{{ rutaAccion?.nombre }}</p>
          <div class="space-y-3">
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1">
                Km finales del vehículo *
              </label>
              <input v-model.number="finalizarForm.km_fin" type="number" min="0"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <button @click="modalFinalizar = false" class="px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg">Cancelar</button>
            <button @click="confirmarFinalizar" :disabled="!finalizarForm.km_fin && finalizarForm.km_fin !== 0"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition disabled:opacity-50">
              Finalizar
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Modal Cancelar ── -->
    <Transition name="modal">
      <div v-if="modalCancelar" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40" @click="modalCancelar = false"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
          <h3 class="text-lg font-bold text-gray-900 mb-1">Cancelar ruta</h3>
          <p class="text-sm text-gray-500 mb-4">{{ rutaAccion?.nombre }}</p>
          <label class="block text-xs font-semibold text-gray-600 mb-1">Motivo de cancelación</label>
          <textarea v-model="motivoCancelar" rows="3" placeholder="Ingresa el motivo..."
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none mb-4"></textarea>
          <div class="flex justify-end gap-2">
            <button @click="modalCancelar = false" class="px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg">Volver</button>
            <button @click="confirmarCancelar"
              class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition">
              Cancelar ruta
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch as apiFetchBase } from '../../utils/api.js'
import { apiFetchEmpresa as apiFetch, getEmpresaActiva, setEmpresaActiva } from '../../utils/empresaActiva.js'
import MapaRuta from './MapaRuta.vue'

// ── Estado principal ──────────────────────────────────────────────────────
const rutas       = ref([])
const resumen     = ref({ total: 0, activas: 0, pendientes: 0, finalizadas: 0, canceladas: 0, km_mes: 0, finalizadas_mes: 0 })
const vehiculos   = ref([])
const conductores = ref([])

// ── Superadmin: selector de empresa ──────────────────────────────────────
const usuario    = computed(() => JSON.parse(localStorage.getItem('usuario') || '{}'))
const esSuperadmin = computed(() => usuario.value.rol === 'SUPERADMIN')
const sinEmpresa = ref(false)
const empresas   = ref([])
const empresaActiva = ref(getEmpresaActiva())
const mostrarDropdownEmpresa = ref(false)
const busquedaEmpresa = ref('')
const empresasFiltradas = computed(() =>
  busquedaEmpresa.value
    ? empresas.value.filter(e => e.nombre.toLowerCase().includes(busquedaEmpresa.value.toLowerCase()))
    : empresas.value
)
function seleccionarEmpresa(emp) {
  setEmpresaActiva(emp)
  empresaActiva.value = { id: emp.id, nombre: emp.nombre }
  mostrarDropdownEmpresa.value = false
  busquedaEmpresa.value = ''
  sinEmpresa.value = false
  Promise.all([cargarRutas(), cargarVehiculos(), cargarConductores()])
}
const cargando = ref(false)

const tabs = [
  { key: 'todas',      label: 'Todas' },
  { key: 'activo',     label: 'Activas' },
  { key: 'pendiente',  label: 'Pendientes' },
  { key: 'finalizado', label: 'Finalizadas' },
]
const tabActivo = ref('todas')

// ── Panel lateral ─────────────────────────────────────────────────────────
const panelAbierto = ref(false)
const rutaDetalle  = ref(null)
const tabPanel     = ref('detalle')

// ── Historial / comentarios ───────────────────────────────────────────────
const eventos           = ref([])
const cargandoEventos   = ref(false)
const nuevoComentario   = ref('')
const enviandoComentario = ref(false)

async function cargarEventos(rutaId) {
  cargandoEventos.value = true
  try {
    const res = await apiFetch(`/api/empresa/rutas/${rutaId}/comentarios/`)
    if (res.ok) {
      eventos.value = await res.json()
    }
  } finally {
    cargandoEventos.value = false
  }
}

async function enviarComentario() {
  if (!nuevoComentario.value.trim() || enviandoComentario.value) return
  enviandoComentario.value = true
  try {
    const res = await apiFetch(`/api/empresa/rutas/${rutaDetalle.value.id}/comentarios/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: nuevoComentario.value.trim() }),
    })
    if (res.ok) {
      const evento = await res.json()
      eventos.value.push(evento)
      nuevoComentario.value = ''
    }
  } finally {
    enviandoComentario.value = false
  }
}

async function cambiarTabPanel(tab) {
  tabPanel.value = tab
  if (tab === 'historial' && rutaDetalle.value?.id) {
    await cargarEventos(rutaDetalle.value.id)
  }
}

// ── Modal crear/editar ────────────────────────────────────────────────────
const modalCrear    = ref(false)
const modoEdicion   = ref(false)
const editandoId    = ref(null)
const paso          = ref(1)
const guardando     = ref(false)
const calculando    = ref(false)
const calculoResult = ref(null)
const errorModal    = ref('')

// ── Validación pre-vuelo ──────────────────────────────────────────────────
const validando             = ref(false)
const validacionResult      = ref(null)   // { errores: [], advertencias: [] }
const advertenciasAceptadas = ref(false)

const formInicial = () => ({
  tipo: 'carga',
  nombre: '',
  conductor_id: null,
  vehiculo_id: null,
  fecha_programada: '',
  hora_programada: '',
  notas: '',
  paradas: [
    { tipo: 'origen',  orden: 0, nombre: '', direccion: '', latitud: null, longitud: null, notas: '' },
    { tipo: 'destino', orden: 1, nombre: '', direccion: '', latitud: null, longitud: null, notas: '' },
  ],
})
const form = ref(formInicial())

// ── Geocoding ─────────────────────────────────────────────────────────────
const geoSugerencias = ref({})
const geoTimers      = {}

// ── Modales de acción ─────────────────────────────────────────────────────
const rutaAccion     = ref(null)
const modalFinalizar = ref(false)
const finalizarForm  = ref({ km_fin: '' })
const modalCancelar  = ref(false)
const motivoCancelar = ref('')

// ── Computed ──────────────────────────────────────────────────────────────
const rutasFiltradas = computed(() =>
  tabActivo.value === 'todas' ? rutas.value : rutas.value.filter(r => r.estado === tabActivo.value)
)

// ── Autocompletado conductor ↔ vehículo ───────────────────────────────────
const autoFillConductor = ref(false)
const autoFillVehiculo  = ref(false)

function onConductorChange() {
  autoFillConductor.value = false
  autoFillVehiculo.value  = false
  validacionResult.value      = null
  advertenciasAceptadas.value = false
  const id = form.value.conductor_id
  if (!id) return
  const conductor  = conductores.value.find(c => c.id === id)
  const vehiculoId = conductor?.vehiculo?.id
    ?? vehiculos.value.find(v => v.conductor_asignado?.id === id)?.id
  if (vehiculoId) {
    form.value.vehiculo_id = vehiculoId
    autoFillVehiculo.value = true
  }
}

function onVehiculoChange() {
  autoFillConductor.value = false
  autoFillVehiculo.value  = false
  validacionResult.value      = null
  advertenciasAceptadas.value = false
  const id = form.value.vehiculo_id
  if (!id) return
  const vehiculo    = vehiculos.value.find(v => v.id === id)
  const conductorId = vehiculo?.conductor_asignado?.id
    ?? conductores.value.find(c => c.vehiculo?.id === id)?.id
  if (conductorId) {
    form.value.conductor_id = conductorId
    autoFillConductor.value = true
  }
}

// ── Carga de datos ────────────────────────────────────────────────────────
async function cargarRutas() {
  cargando.value = true
  try {
    const res = await apiFetch('/api/empresa/rutas/')
    if (res.status === 400) {
      const d = await res.json()
      if (d.error === 'sin_empresa') { sinEmpresa.value = true; return }
    }
    if (!res.ok) return
    sinEmpresa.value = false
    const data = await res.json()
    rutas.value   = data.rutas || []
    resumen.value = data.resumen || resumen.value
  } finally {
    cargando.value = false
  }
}

async function cargarVehiculos() {
  const res = await apiFetch('/api/empresa/vehiculos/')
  if (!res.ok) return
  const data = await res.json()
  vehiculos.value = Array.isArray(data) ? data : (data.vehiculos || data.results || [])
}

async function cargarConductores() {
  const res = await apiFetch('/api/empresa/conductores/')
  if (!res.ok) return
  const data = await res.json()
  conductores.value = Array.isArray(data) ? data : (data.conductores || data.results || [])
}

// ── Panel lateral ─────────────────────────────────────────────────────────
async function abrirPanel(ruta) {
  panelAbierto.value = true
  tabPanel.value     = 'detalle'
  eventos.value      = []
  rutaDetalle.value  = { ...ruta }
  const res = await apiFetch(`/api/empresa/rutas/${ruta.id}/`)
  if (res.ok) {
    rutaDetalle.value = await res.json()
  }
}

// ── Modal crear / editar ──────────────────────────────────────────────────
function abrirModalCrear() {
  modoEdicion.value   = false
  editandoId.value    = null
  form.value          = formInicial()
  calculoResult.value = null
  paso.value          = 1
  modalCrear.value    = true
}

function abrirModalEditar(ruta) {
  modoEdicion.value = true
  editandoId.value  = ruta.id
  form.value = {
    tipo:             ruta.tipo,
    nombre:           ruta.nombre,
    conductor_id:     ruta.conductor_id,
    vehiculo_id:      ruta.vehiculo_id,
    fecha_programada: ruta.fecha_programada || '',
    hora_programada:  ruta.hora_programada  || '',
    notas:            ruta.notas || '',
    paradas: (ruta.paradas || []).map(p => ({
      tipo:      p.tipo,
      orden:     p.orden,
      nombre:    p.nombre,
      direccion: p.direccion,
      latitud:   p.latitud,
      longitud:  p.longitud,
      notas:     p.notas || '',
    })),
  }
  if (!form.value.paradas.some(p => p.tipo === 'origen')) {
    form.value.paradas.unshift({ tipo: 'origen', orden: 0, nombre: '', direccion: '', latitud: null, longitud: null, notas: '' })
  }
  if (!form.value.paradas.some(p => p.tipo === 'destino')) {
    form.value.paradas.push({ tipo: 'destino', orden: 99, nombre: '', direccion: '', latitud: null, longitud: null, notas: '' })
  }
  calculoResult.value = null
  paso.value          = 1
  modalCrear.value    = true
}

function cerrarModal() {
  modalCrear.value            = false
  errorModal.value            = ''
  geoSugerencias.value        = {}
  autoFillConductor.value     = false
  autoFillVehiculo.value      = false
  validacionResult.value      = null
  advertenciasAceptadas.value = false
}

async function siguientePaso() {
  errorModal.value = ''

  if (paso.value === 1) {
    // Validación de fecha
    if (form.value.fecha_programada) {
      const hoy     = new Date(); hoy.setHours(0, 0, 0, 0)
      const elegida = new Date(form.value.fecha_programada + 'T00:00:00')
      if (elegida < hoy) {
        errorModal.value = 'La fecha programada no puede ser anterior a hoy.'
        return
      }
    }

    // Pre-flight: validar conductor + vehículo
    if ((form.value.conductor_id || form.value.vehiculo_id) && !advertenciasAceptadas.value) {
      validando.value = true
      try {
        const res = await apiFetch('/api/empresa/rutas/validar/', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({
            conductor_id:     form.value.conductor_id,
            vehiculo_id:      form.value.vehiculo_id,
            fecha_programada: form.value.fecha_programada || null,
            ruta_id:          modoEdicion.value ? editandoId.value : null,
          }),
        })
        const data = res.ok ? await res.json() : { errores: [], advertencias: [] }
        validacionResult.value = data

        // Si hay errores duros → bloquear
        if (data.errores?.length) { validando.value = false; return }

        // Si hay advertencias → mostrar panel y esperar confirmación del usuario
        if (data.advertencias?.length) { validando.value = false; return }
      } catch {
        // Si el endpoint falla no bloqueamos la creación
        validacionResult.value = null
      }
      validando.value = false
    }

    paso.value++
    return
  }

  if (paso.value === 2) {
    paso.value = 3
    await ejecutarCalculo()
  } else {
    paso.value++
  }
}

async function ejecutarCalculo() {
  calculando.value    = true
  calculoResult.value = null
  const payload = {
    paradas: form.value.paradas.filter(p => p.latitud && p.longitud).map((p, i) => ({
      tipo: p.tipo, orden: i, nombre: p.nombre, lat: p.latitud, lng: p.longitud,
    })),
  }
  try {
    const res = await apiFetch('/api/empresa/rutas/calcular/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    calculoResult.value = res.ok ? await res.json() : null
  } catch {
    calculoResult.value = null
  } finally {
    calculando.value = false
  }
}

async function guardarRuta() {
  guardando.value  = true
  errorModal.value = ''
  const payload = {
    tipo:             form.value.tipo,
    nombre:           form.value.nombre,
    conductor_id:     form.value.conductor_id,
    vehiculo_id:      form.value.vehiculo_id,
    fecha_programada: form.value.fecha_programada || null,
    hora_programada:  form.value.hora_programada  || null,
    notas:            form.value.notas,
    paradas:          form.value.paradas.map((p, i) => ({
      tipo: p.tipo, orden: i, nombre: p.nombre, direccion: p.direccion,
      lat: p.latitud, lng: p.longitud, notas: p.notas || '',
    })),
  }
  const url    = modoEdicion.value ? `/api/empresa/rutas/${editandoId.value}/` : '/api/empresa/rutas/'
  const method = modoEdicion.value ? 'PUT' : 'POST'
  try {
    const res = await apiFetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (res.ok) {
      const data = await res.json()
      cerrarModal()
      await cargarRutas()
      toast('exito', modoEdicion.value ? 'Ruta actualizada correctamente.' : 'Ruta creada correctamente.')
      if (data.aviso) setTimeout(() => toast('info', data.aviso), 400)
    } else {
      const errData = await res.json().catch(() => ({}))
      const msgs = [errData.fecha_programada, errData.conductor_id, errData.vehiculo_id, errData.error].filter(Boolean)
      errorModal.value = msgs.length ? msgs.join('\n') : (errData.detail || 'No se pudo guardar la ruta.')
    }
  } catch {
    errorModal.value = 'Error de conexión al guardar la ruta.'
  } finally {
    guardando.value = false
  }
}

// ── Geocoding Nominatim ───────────────────────────────────────────────────
function buscarDireccion(texto, idx) {
  form.value.paradas[idx].nombre   = texto
  form.value.paradas[idx].latitud  = null
  form.value.paradas[idx].longitud = null
  if (geoTimers[idx]) clearTimeout(geoTimers[idx])
  if (!texto || texto.length < 3) { geoSugerencias.value[idx] = []; return }
  geoTimers[idx] = setTimeout(async () => {
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(texto)}&countrycodes=cl&limit=5`
      const res = await fetch(url, { headers: { 'Accept-Language': 'es' } })
      geoSugerencias.value[idx] = await res.json()
    } catch {
      geoSugerencias.value[idx] = []
    }
  }, 500)
}

function seleccionarDireccion(sug, idx) {
  const partes = sug.display_name.split(',')
  form.value.paradas[idx].nombre    = partes[0].trim()
  form.value.paradas[idx].direccion = sug.display_name
  form.value.paradas[idx].latitud   = parseFloat(sug.lat)
  form.value.paradas[idx].longitud  = parseFloat(sug.lon)
  geoSugerencias.value[idx] = []
}

function agregarParada() {
  const destinoIdx = form.value.paradas.findIndex(p => p.tipo === 'destino')
  form.value.paradas.splice(destinoIdx, 0, { tipo: 'parada', orden: destinoIdx, nombre: '', direccion: '', latitud: null, longitud: null, notas: '' })
  form.value.paradas.forEach((p, i) => { p.orden = i })
}

function quitarParada(idx) {
  form.value.paradas.splice(idx, 1)
  form.value.paradas.forEach((p, i) => { p.orden = i })
}

// ── Acciones de ruta ──────────────────────────────────────────────────────
async function prepararIniciar(ruta) {
  const res = await apiFetch(`/api/empresa/rutas/${ruta.id}/iniciar/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
  })
  if (res.ok) { await cargarRutas(); toast('exito', 'Ruta iniciada.') }
  else { const err = await res.json(); toast('error', err.error || 'Error al iniciar la ruta.') }
}

function prepararFinalizar(ruta) {
  rutaAccion.value = ruta
  const distancia  = Math.round(ruta.distancia_km || 0)
  const kmFin      = ruta.km_inicio != null ? ruta.km_inicio + distancia : distancia || ''
  finalizarForm.value = { km_fin: kmFin }
  modalFinalizar.value = true
}

async function confirmarFinalizar() {
  const res = await apiFetch(`/api/empresa/rutas/${rutaAccion.value.id}/finalizar/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(finalizarForm.value),
  })
  if (res.ok) { modalFinalizar.value = false; await cargarRutas(); toast('exito', 'Ruta finalizada.') }
  else { const err = await res.json(); toast('error', err.error || 'Error al finalizar la ruta.') }
}

function prepararCancelar(ruta) {
  rutaAccion.value     = ruta
  motivoCancelar.value = ''
  modalCancelar.value  = true
}

async function confirmarCancelar() {
  const res = await apiFetch(`/api/empresa/rutas/${rutaAccion.value.id}/cancelar/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ motivo: motivoCancelar.value }),
  })
  if (res.ok) { modalCancelar.value = false; await cargarRutas(); toast('exito', 'Ruta cancelada.') }
  else { const err = await res.json(); toast('error', err.error || 'Error al cancelar la ruta.') }
}

// ── Helpers ───────────────────────────────────────────────────────────────
function formatFecha(s) {
  if (!s) return '—'
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

function formatDuracion(min) {
  if (!min) return '—'
  const h = Math.floor(min / 60)
  const m = min % 60
  return h > 0 ? `${h}h ${m}min` : `${m} min`
}

function formatTimestamp(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('es-CL', { day: '2-digit', month: 'short' }) +
    ' ' + d.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })
}

function badgeEstado(estado) {
  return {
    activo:     'bg-green-100 text-green-700',
    pendiente:  'bg-blue-100 text-blue-700',
    finalizado: 'bg-gray-100 text-gray-600',
    cancelado:  'bg-red-100 text-red-600',
    borrador:   'bg-yellow-100 text-yellow-700',
  }[estado] || 'bg-gray-100 text-gray-600'
}

function labelEstado(estado) {
  return {
    activo: 'Activo', pendiente: 'Pendiente',
    finalizado: 'Finalizado', cancelado: 'Cancelado', borrador: 'Borrador',
  }[estado] || estado
}

function toast(tipo, mensaje) {
  // AppToast espera { msg, tipo } con tipo = 'success' | 'error' | 'info'
  const tipoNorm = tipo === 'exito' ? 'success' : tipo
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { msg: mensaje, tipo: tipoNorm } }))
}

// ── Inicialización ────────────────────────────────────────────────────────
onMounted(async () => {
  if (esSuperadmin.value) {
    const res = await apiFetchBase('/api/empresas/')
    if (res.ok) {
      const data = await res.json()
      empresas.value = Array.isArray(data) ? data : []
    }
  }
  await Promise.all([cargarRutas(), cargarVehiculos(), cargarConductores()])
})
</script>

<style scoped>
.panel-enter-active, .panel-leave-active { transition: opacity 0.2s; }
.panel-enter-from, .panel-leave-to { opacity: 0; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.15s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.fade-slide-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.fade-slide-leave-active { transition: opacity 0.15s ease; }
.fade-slide-enter-from { opacity: 0; transform: translateY(-6px); }
.fade-slide-leave-to   { opacity: 0; }
</style>
