import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom'
import { render, screen, waitFor } from '@testing-library/react'
import App from './App'

vi.mock('./api/client', () => ({
  checkHealth: vi.fn(),
  checkDbHealth: vi.fn(),
}))

import { checkHealth, checkDbHealth } from './api/client'

describe('App', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows loading state initially', () => {
    render(<App />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('displays health info when API responds', async () => {
    checkHealth.mockResolvedValue({ status: 'ok', app: 'vector-studio', environment: 'development' })
    checkDbHealth.mockResolvedValue({ status: 'ok', database: 'connected' })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('development')).toBeInTheDocument()
      expect(screen.getByText('connected')).toBeInTheDocument()
    })
  })

  it('displays error when API fails', async () => {
    checkHealth.mockRejectedValue(new Error('Network error'))
    checkDbHealth.mockResolvedValue({ status: 'ok', database: 'connected' })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })
})