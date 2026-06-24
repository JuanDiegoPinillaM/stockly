import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PasswordField from './PasswordField.vue'

describe('PasswordField', () => {
  it('alterna entre ocultar y mostrar la contraseña', async () => {
    const wrapper = mount(PasswordField, {
      props: { id: 'pw', modelValue: 'secreto' }
    })
    const input = wrapper.get('input')
    expect(input.attributes('type')).toBe('password')

    await wrapper.get('.auth-input__toggle').trigger('click')
    expect(input.attributes('type')).toBe('text')

    await wrapper.get('.auth-input__toggle').trigger('click')
    expect(input.attributes('type')).toBe('password')
  })

  it('emite update:modelValue al escribir', async () => {
    const wrapper = mount(PasswordField, {
      props: { id: 'pw', modelValue: '' }
    })
    await wrapper.get('input').setValue('abc123')
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['abc123'])
  })
})
