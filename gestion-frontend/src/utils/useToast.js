const EVENT = 'app-toast'

export const useToast = () => ({
  success: (msg)           => window.dispatchEvent(new CustomEvent(EVENT, { detail: { msg, tipo: 'success' } })),
  error:   (msg)           => window.dispatchEvent(new CustomEvent(EVENT, { detail: { msg, tipo: 'error'   } })),
  info:    (msg)           => window.dispatchEvent(new CustomEvent(EVENT, { detail: { msg, tipo: 'info'    } })),
  agregar: (msg, tipo = 'info') => window.dispatchEvent(new CustomEvent(EVENT, { detail: { msg, tipo } })),
})
