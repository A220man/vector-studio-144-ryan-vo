export const API_BASE = '/api'

export interface HealthResponse {
  status: string
  app: string
  environment: string
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`)
  }
  return response.json()
}

export async function checkDbHealth(): Promise<{ status: string; database: string }> {
  const response = await fetch(`${API_BASE}/health/db`)
  if (!response.ok) {
    throw new Error(`DB health check failed: ${response.statusText}`)
  }
  return response.json()
}