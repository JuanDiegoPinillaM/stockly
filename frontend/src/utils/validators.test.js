import { describe, it, expect } from 'vitest'
import { isEmail, required, email, minLength, matches, onlyDigits, phone, formatPhone, formatNit } from './validators'

describe('validators', () => {
  it('isEmail distingue correos válidos e inválidos', () => {
    expect(isEmail('juan@test.com')).toBe(true)
    expect(isEmail('sin-arroba.com')).toBe(false)
    expect(isEmail('')).toBe(false)
  })

  it('required exige un valor no vacío', () => {
    expect(required('algo')).toBe('')
    expect(required('   ')).not.toBe('')
    expect(required('')).not.toBe('')
  })

  it('email devuelve mensaje cuando es inválido', () => {
    expect(email('a@b.com')).toBe('')
    expect(email('malo')).not.toBe('')
  })

  it('minLength valida la longitud mínima', () => {
    expect(minLength('abcd', 3)).toBe('')
    expect(minLength('ab', 3)).toContain('3')
  })

  it('matches compara dos valores', () => {
    expect(matches('clave', 'clave')).toBe('')
    expect(matches('clave', 'otra')).not.toBe('')
  })

  it('onlyDigits descarta todo lo que no sea número', () => {
    expect(onlyDigits('300 123 4567')).toBe('3001234567')
    expect(onlyDigits('+57 (300) 123-4567')).toBe('573001234567')
  })

  it('phone exige exactamente 10 dígitos', () => {
    expect(phone('300 123 4567')).toBe('')
    expect(phone('3001234567')).toBe('')
    expect(phone('30012345')).not.toBe('')
    expect(phone('30012345678')).not.toBe('')
    expect(phone('')).not.toBe('')
  })

  it('formatPhone agrupa 3-3-4 y recorta a 10 dígitos', () => {
    expect(formatPhone('3001234567')).toBe('300 123 4567')
    expect(formatPhone('300123456789')).toBe('300 123 4567')
    expect(formatPhone('300')).toBe('300')
    expect(formatPhone('300123')).toBe('300 123')
  })

  it('formatNit agrupa con puntos y separa el dígito de verificación', () => {
    expect(formatNit('9001234567')).toBe('900.123.456-7')
    expect(formatNit('900.123.456-7')).toBe('900.123.456-7')
    expect(formatNit('8')).toBe('8')
    expect(formatNit('12')).toBe('1-2')
  })
})
