<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'

const pagos           = ref([])
const cargando        = ref(true)
const error           = ref('')
const pagoImprimiendo = ref(null)   // pago activo en el modal de comprobante

onMounted(async () => {
  try {
    const res  = await apiFetch('/api/pago/historial/')
    if (!res.ok) { error.value = 'No se pudo cargar el historial.'; return }
    const data = await res.json()
    pagos.value = data.pagos || []
  } catch {
    error.value = 'Error de conexión.'
  } finally {
    cargando.value = false
  }
})

function formatCLP(n) {
  return '$' + parseInt(n).toLocaleString('es-CL')
}

function exportarCSV() {
  if (!pagos.value.length) return
  const headers = ['Orden', 'Empresa', 'Plan', 'Ciclo', 'Monto', 'Fecha', 'Estado']
  const rows    = pagos.value.map(p => [
    p.orden_compra,
    p.empresa_nombre || '',
    p.plan,
    p.ciclo,
    p.monto,
    p.fecha || '',
    p.estado,
  ])
  const csv  = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = 'historial_pagos.csv'; a.click()
  URL.revokeObjectURL(url)
}

// ── Comprobante ──────────────────────────────────────────────────────
function verComprobante(pago) {
  pagoImprimiendo.value = pago
}

function cerrarComprobante() {
  pagoImprimiendo.value = null
}

function imprimirComprobante() {
  const p = pagoImprimiendo.value
  if (!p) return

  const viaLabel = p.via === 'oneclick' || p.via === 'autocobro'
    ? 'Tarjeta guardada (OneClick)'
    : 'Webpay Plus (tarjeta nueva)'

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Comprobante ${p.orden_compra}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: Arial, Helvetica, sans-serif;
      background: #fff;
      padding: 48px 40px;
      max-width: 520px;
      margin: 0 auto;
      color: #111827;
    }
    .logo {
      font-size: 1.25rem;
      font-weight: 800;
      color: #4F46E5;
      letter-spacing: -0.5px;
      margin-bottom: 4px;
    }
    .titulo {
      font-size: 0.875rem;
      color: #6B7280;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-bottom: 28px;
    }
    .estado-badge {
      display: inline-block;
      background: #D1FAE5;
      color: #065F46;
      font-size: 0.8125rem;
      font-weight: 700;
      padding: 4px 14px;
      border-radius: 99px;
      margin-bottom: 24px;
    }
    .divider {
      border: none;
      border-top: 1px solid #E5E7EB;
      margin: 20px 0;
    }
    .fila {
      display: flex;
      justify-content: space-between;
      padding: 7px 0;
      font-size: 0.9rem;
    }
    .fila .label { color: #6B7280; }
    .fila .valor { font-weight: 600; color: #111827; text-align: right; }
    .fila-monto .valor {
      font-size: 1.25rem;
      font-weight: 800;
      color: #4F46E5;
    }
    .orden {
      font-family: 'Courier New', monospace;
      font-size: 0.8125rem;
      color: #6B7280;
    }
    .nota {
      margin-top: 32px;
      padding: 12px 16px;
      background: #F9FAFB;
      border: 1px solid #E5E7EB;
      border-radius: 6px;
      font-size: 0.75rem;
      color: #9CA3AF;
      line-height: 1.5;
    }
    .footer {
      margin-top: 40px;
      font-size: 0.75rem;
      color: #D1D5DB;
      text-align: center;
    }
    @media print {
      body { padding: 20px; }
    }
  </style>
</head>
<body>
  <div class="logo">🚛 Gestión de Flota</div>
  <div class="titulo">Comprobante de pago</div>

  <div class="estado-badge">✓ Pago aprobado</div>

  <div class="fila">
    <span class="label">N° Orden</span>
    <span class="valor orden">${p.orden_compra}</span>
  </div>
  <div class="fila">
    <span class="label">Empresa</span>
    <span class="valor">${p.empresa_nombre || '—'}${p.empresa_rut ? ' · ' + p.empresa_rut : ''}</span>
  </div>

  <hr class="divider">

  <div class="fila">
    <span class="label">Plan</span>
    <span class="valor">${p.plan}</span>
  </div>
  <div class="fila">
    <span class="label">Ciclo de facturación</span>
    <span class="valor" style="text-transform:capitalize">${p.ciclo}</span>
  </div>
  <div class="fila">
    <span class="label">Medio de pago</span>
    <span class="valor">${viaLabel}</span>
  </div>
  <div class="fila">
    <span class="label">Fecha de pago</span>
    <span class="valor">${p.fecha || '—'}</span>
  </div>

  <hr class="divider">

  <div class="fila fila-monto">
    <span class="label" style="font-size:1rem;font-weight:700;color:#111827">Total pagado</span>
    <span class="valor">${formatCLP(p.monto)}</span>
  </div>

  <div class="nota">
    ⚠ Este documento es un comprobante interno de pago generado por el sistema de gestión de flota.
    <strong>No constituye un documento tributario (boleta o factura electrónica)</strong>
    válido para el Servicio de Impuestos Internos (SII).
  </div>

  <div class="footer">
    Generado el ${new Date().toLocaleDateString('es-CL', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })}
  </div>

  <script>
    window.onload = function() {
      setTimeout(function() { window.print(); }, 400);
    };
  <\/script>
</body>
</html>`

  const win = window.open('', '_blank', 'width=620,height=780')
  if (win) {
    win.document.write(html)
    win.document.close()
  }
}
</script>

<template>
  <div class="historial-page">

    <!-- Encabezado -->
    <div class="historial-header">
      <div>
        <h1 class="historial-title">Historial de pagos</h1>
        <p class="historial-sub">Pagos aprobados de tu suscripción</p>
      </div>
      <button v-if="pagos.length" class="btn-export" @click="exportarCSV">
        ↓ Exportar CSV
      </button>
    </div>

    <div v-if="cargando"        class="estado-msg">Cargando…</div>
    <div v-else-if="error"      class="error-box">{{ error }}</div>
    <div v-else-if="!pagos.length" class="estado-msg">No hay pagos registrados aún.</div>

    <div v-else class="tabla-wrap">
      <table class="tabla">
        <thead>
          <tr>
            <th>Orden</th>
            <th>Plan</th>
            <th>Ciclo</th>
            <th>Monto</th>
            <th>Fecha</th>
            <th>Estado</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in pagos" :key="p.id">
            <td class="orden-col">{{ p.orden_compra }}</td>
            <td>{{ p.plan }}</td>
            <td class="cap">{{ p.ciclo }}</td>
            <td>{{ formatCLP(p.monto) }}</td>
            <td>{{ p.fecha }}</td>
            <td><span class="badge-ok">Aprobado</span></td>
            <td>
              <button class="btn-comprobante" @click="verComprobante(p)">
                🧾 Comprobante
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── Modal comprobante ─────────────────────────────────────── -->
    <div v-if="pagoImprimiendo" class="modal-overlay" @click.self="cerrarComprobante">
      <div class="modal-box">

        <!-- Cabecera modal -->
        <div class="modal-header">
          <h2 class="modal-titulo">Comprobante de pago</h2>
          <button class="modal-cerrar" @click="cerrarComprobante">✕</button>
        </div>

        <!-- Contenido del comprobante (preview) -->
        <div class="comprobante-preview">
          <div class="comp-logo">🚛 Gestión de Flota</div>
          <div class="comp-subtitulo">Comprobante de pago</div>

          <div class="comp-badge">✓ Pago aprobado</div>

          <div class="comp-fila">
            <span class="comp-label">N° Orden</span>
            <span class="comp-valor mono">{{ pagoImprimiendo.orden_compra }}</span>
          </div>
          <div class="comp-fila">
            <span class="comp-label">Empresa</span>
            <span class="comp-valor">{{ pagoImprimiendo.empresa_nombre || '—' }}
              <small v-if="pagoImprimiendo.empresa_rut"> · {{ pagoImprimiendo.empresa_rut }}</small>
            </span>
          </div>

          <div class="comp-divider"/>

          <div class="comp-fila">
            <span class="comp-label">Plan</span>
            <span class="comp-valor">{{ pagoImprimiendo.plan }}</span>
          </div>
          <div class="comp-fila">
            <span class="comp-label">Ciclo</span>
            <span class="comp-valor cap">{{ pagoImprimiendo.ciclo }}</span>
          </div>
          <div class="comp-fila">
            <span class="comp-label">Medio de pago</span>
            <span class="comp-valor">
              {{ pagoImprimiendo.via === 'oneclick' || pagoImprimiendo.via === 'autocobro'
                  ? 'Tarjeta guardada (OneClick)'
                  : 'Webpay Plus' }}
            </span>
          </div>
          <div class="comp-fila">
            <span class="comp-label">Fecha de pago</span>
            <span class="comp-valor">{{ pagoImprimiendo.fecha || '—' }}</span>
          </div>

          <div class="comp-divider"/>

          <div class="comp-fila comp-total">
            <span class="comp-label-total">Total pagado</span>
            <span class="comp-valor-total">{{ formatCLP(pagoImprimiendo.monto) }}</span>
          </div>

          <div class="comp-nota">
            ⚠ Este documento es un comprobante interno. <strong>No es un DTE válido para el SII.</strong>
          </div>
        </div>

        <!-- Acciones -->
        <div class="modal-footer">
          <button class="btn-imprimir" @click="imprimirComprobante">
            🖨 Imprimir / Guardar PDF
          </button>
          <button class="btn-cerrar-modal" @click="cerrarComprobante">Cerrar</button>
        </div>

      </div>
    </div>

  </div>
</template>

<style scoped>
.historial-page   { padding: 2rem 2.5rem; max-width: 960px; margin: 0 auto; }
.historial-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem; }
.historial-title  { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0 0 .25rem; }
.historial-sub    { font-size: .875rem; color: #6B7280; margin: 0; }

.btn-export {
  padding: .5rem 1rem; background: #fff; border: 1px solid #E5E7EB;
  border-radius: 8px; font-size: .8125rem; color: #374151; cursor: pointer; font-family: inherit;
}
.btn-export:hover { background: #F9FAFB; }

.estado-msg { color: #6B7280; font-size: .9rem; padding: 2rem 0; }
.error-box  { background: #FEF2F2; border: 1px solid #FECACA; color: #B91C1C; padding: .75rem 1rem; border-radius: 8px; font-size: .875rem; }

.tabla-wrap { overflow-x: auto; }
.tabla      { width: 100%; border-collapse: collapse; font-size: .875rem; }
.tabla thead th {
  text-align: left; padding: .625rem .875rem;
  background: #F9FAFB; color: #374151; font-weight: 600;
  border-bottom: 1px solid #E5E7EB; white-space: nowrap;
}
.tabla tbody tr:hover { background: #F9FAFB; }
.tabla tbody td { padding: .625rem .875rem; border-bottom: 1px solid #F3F4F6; color: #374151; }
.orden-col  { font-family: monospace; font-size: .8rem; color: #6B7280; }
.cap        { text-transform: capitalize; }
.badge-ok   { background: #D1FAE5; color: #065F46; font-size: .75rem; font-weight: 600; padding: 2px 10px; border-radius: 99px; }
.btn-comprobante {
  padding: .3rem .7rem; background: #EEF2FF; border: 1px solid #C7D2FE;
  border-radius: 6px; font-size: .8rem; color: #4338CA; cursor: pointer;
  font-family: inherit; white-space: nowrap;
}
.btn-comprobante:hover { background: #E0E7FF; }

/* ── Modal ──────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.5);
  display: flex; align-items: center; justify-content: center; z-index: 9999;
  padding: 1rem;
}
.modal-box {
  background: #fff; border-radius: 16px; width: 100%; max-width: 480px;
  box-shadow: 0 20px 60px rgba(0,0,0,.2); display: flex; flex-direction: column;
  max-height: 90vh; overflow: hidden;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid #F3F4F6;
}
.modal-titulo   { font-size: 1.0625rem; font-weight: 700; color: #111827; margin: 0; }
.modal-cerrar   {
  width: 28px; height: 28px; border-radius: 50%; border: none;
  background: #F3F4F6; color: #6B7280; cursor: pointer; font-size: .875rem;
  display: flex; align-items: center; justify-content: center; font-family: inherit;
}
.modal-cerrar:hover { background: #E5E7EB; }

/* Comprobante preview */
.comprobante-preview { padding: 1.5rem; overflow-y: auto; flex: 1; }
.comp-logo     { font-size: 1.125rem; font-weight: 800; color: #4F46E5; margin-bottom: 2px; }
.comp-subtitulo { font-size: .75rem; text-transform: uppercase; letter-spacing: .08em; color: #9CA3AF; margin-bottom: 1rem; }
.comp-badge    {
  display: inline-block; background: #D1FAE5; color: #065F46;
  font-size: .8125rem; font-weight: 700; padding: 3px 12px;
  border-radius: 99px; margin-bottom: 1rem;
}
.comp-fila     { display: flex; justify-content: space-between; align-items: baseline; padding: .4rem 0; font-size: .875rem; }
.comp-label    { color: #6B7280; }
.comp-valor    { font-weight: 600; color: #111827; text-align: right; }
.comp-valor.mono { font-family: monospace; font-size: .8125rem; color: #6B7280; }
.comp-divider  { border: none; border-top: 1px solid #F3F4F6; margin: .75rem 0; }
.comp-total    { margin-top: .25rem; }
.comp-label-total { font-size: 1rem; font-weight: 700; color: #111827; }
.comp-valor-total { font-size: 1.375rem; font-weight: 800; color: #4F46E5; }
.comp-nota {
  margin-top: 1rem; padding: .75rem 1rem; background: #F9FAFB;
  border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: .75rem; color: #9CA3AF; line-height: 1.5;
}

.modal-footer {
  display: flex; gap: .75rem; padding: 1rem 1.5rem;
  border-top: 1px solid #F3F4F6; flex-wrap: wrap;
}
.btn-imprimir {
  flex: 1; padding: .7rem 1.25rem; background: #4F46E5; color: #fff;
  border: none; border-radius: 8px; font-size: .9375rem; font-weight: 600;
  cursor: pointer; font-family: inherit;
}
.btn-imprimir:hover { background: #4338CA; }
.btn-cerrar-modal {
  padding: .7rem 1.25rem; background: #fff; color: #374151;
  border: 1px solid #E5E7EB; border-radius: 8px; font-size: .9375rem;
  cursor: pointer; font-family: inherit;
}
.btn-cerrar-modal:hover { background: #F9FAFB; }
</style>
