/**
 * Validadores reutilizables para los formularios.
 * Devuelven un string vacío si es válido, o el mensaje de error si no lo es.
 */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Teléfono colombiano: exactamente 10 dígitos.
const PHONE_DIGITS = 10

export const isEmail = (value) => EMAIL_RE.test(String(value ?? '').trim())

/** Solo los dígitos de un valor (descarta espacios, guiones, +, etc.). */
export const onlyDigits = (value) => String(value ?? '').replace(/\D/g, '')

/** Valida que el teléfono tenga exactamente 10 dígitos. */
export const phone = (value, message = 'El teléfono debe tener 10 dígitos') =>
  onlyDigits(value).length === PHONE_DIGITS ? '' : message

/** Formatea "3001234567" → "300 123 4567" (agrupa 3-3-4, recorta a 10 dígitos). */
export const formatPhone = (value) => {
  const d = onlyDigits(value).slice(0, PHONE_DIGITS)
  return [d.slice(0, 3), d.slice(3, 6), d.slice(6, 10)].filter(Boolean).join(' ')
}

/** Formatea un NIT colombiano: el último dígito es el de verificación.
 * "9001234567" → "900.123.456-7". */
export const formatNit = (value) => {
  const digits = onlyDigits(value)
  if (digits.length < 2) return digits
  const body = digits.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${body}-${digits.slice(-1)}`
}

export const required = (value, message = 'Este campo es obligatorio') =>
  String(value ?? '').trim().length > 0 ? '' : message

export const email = (value, message = 'Ingresa un correo válido') =>
  isEmail(value) ? '' : message

export const minLength = (value, n, message) =>
  String(value ?? '').length >= n ? '' : message || `Mínimo ${n} caracteres`

export const matches = (a, b, message = 'Los valores no coinciden') => (a === b ? '' : message)
