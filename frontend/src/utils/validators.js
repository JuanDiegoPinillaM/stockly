/**
 * Validadores reutilizables para los formularios.
 * Devuelven un string vacío si es válido, o el mensaje de error si no lo es.
 */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const isEmail = (value) => EMAIL_RE.test(String(value ?? '').trim())

export const required = (value, message = 'Este campo es obligatorio') =>
  String(value ?? '').trim().length > 0 ? '' : message

export const email = (value, message = 'Ingresa un correo válido') =>
  isEmail(value) ? '' : message

export const minLength = (value, n, message) =>
  String(value ?? '').length >= n ? '' : message || `Mínimo ${n} caracteres`

export const matches = (a, b, message = 'Los valores no coinciden') => (a === b ? '' : message)
