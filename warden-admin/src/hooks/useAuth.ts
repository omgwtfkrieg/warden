import { useState } from 'react'
import { login as apiLogin, logout as apiLogout } from '@/api/auth'

export function useAuth() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isAuthenticated = !!localStorage.getItem('access_token')

  async function login(email: string, password: string): Promise<boolean> {
    setLoading(true)
    setError(null)
    try {
      const tokens = await apiLogin(email, password)
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      return true
    } catch {
      setError('Invalid email or password')
      return false
    } finally {
      setLoading(false)
    }
  }

  async function logout() {
    const refresh_token = localStorage.getItem('refresh_token') ?? ''
    try { await apiLogout(refresh_token) } catch { /* ignore */ }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.location.href = '/login'
  }

  return { isAuthenticated, login, logout, loading, error }
}
