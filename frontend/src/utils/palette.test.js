import { describe, it, expect } from 'vitest'
import { hexToRgb, rgbToHex, palette, inkOn, surfaces, textTokens } from './palette'

describe('palette', () => {
  it('hexToRgb parsea forma larga y corta', () => {
    expect(hexToRgb('#0e6e4e')).toEqual([14, 110, 78])
    expect(hexToRgb('0e6e4e')).toEqual([14, 110, 78])
    expect(hexToRgb('#abc')).toEqual([170, 187, 204])
    expect(hexToRgb('nope')).toBeNull()
  })

  it('rgbToHex formatea con dos dígitos', () => {
    expect(rgbToHex([14, 110, 78])).toBe('#0e6e4e')
    expect(rgbToHex([0, 0, 0])).toBe('#000000')
  })

  it('palette deriva el set completo de tokens', () => {
    const t = palette('#0e6e4e', '#b8923a')
    expect(t['color-primary']).toBe('#0e6e4e')
    expect(t['color-primary-rgb']).toBe('14, 110, 78')
    expect(t).toHaveProperty('color-primary-dark')
    expect(t).toHaveProperty('color-primary-soft')
    expect(t).toHaveProperty('color-accent-soft')
  })

  it('palette devuelve null con color inválido', () => {
    expect(palette('xyz', '#b8923a')).toBeNull()
    expect(palette('#12', '#b8923a')).toBeNull()
  })
})

describe('surfaces', () => {
  it('inkOn elige texto por contraste', () => {
    expect(inkOn('#ffffff')).toBe('#14201a')
    expect(inkOn('#0e1a14')).toBe('#f6f3ec')
    expect(inkOn('#0e6e4e')).toBe('#f6f3ec')
  })

  it('vacío usa los fondos por defecto', () => {
    const t = surfaces({})
    expect(t['color-navbar']).toBe('#faf7f0')
    expect(t['color-footer']).toBe('#0e1a14')
    expect(t['color-footer-ink']).toBe('#f6f3ec')
    expect(t['color-announce']).toBe('#14201a') // tinta por defecto
    // El fondo de página solo se emite si se personaliza.
    expect(t).not.toHaveProperty('color-page')
  })

  it('fondo de página se emite solo personalizado', () => {
    expect(surfaces({ page: '#101010' })['color-page']).toBe('#101010')
  })

  it('override calcula tinta y rgb', () => {
    const t = surfaces({ navbar: '#0e6e4e' })
    expect(t['color-navbar']).toBe('#0e6e4e')
    expect(t['color-navbar-ink']).toBe('#f6f3ec')
    expect(t['color-navbar-rgb']).toBe('14, 110, 78')
  })
})

describe('textTokens', () => {
  it('sin color no cambia nada', () => {
    expect(textTokens('')).toEqual({})
    expect(textTokens('nope')).toEqual({})
  })
  it('sobrescribe tinta y deriva cuerpo', () => {
    const t = textTokens('#222222')
    expect(t['color-ink']).toBe('#222222')
    expect(t['color-ink-rgb']).toBe('34, 34, 34')
    expect(t['color-body']).not.toBe(t['color-ink'])
  })
})
