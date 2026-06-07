import { describe, expect, it } from 'vitest'
import { renderWithProviders } from '../test/renderWithProviders'
import { LoginPage } from './Login'

describe('LoginPage', () => {
  it('renders sign-in form', () => {
    renderWithProviders(<LoginPage />)
    expect(document.querySelector('form')).toBeTruthy()
    expect(document.querySelector('input[type="password"]')).toBeTruthy()
  })
})
