import { describe, it, expect } from 'vitest'
import { isEmail, required, email, minLength, matches } from './validators'

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
})
