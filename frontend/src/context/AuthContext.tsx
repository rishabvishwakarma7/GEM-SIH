import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import apiClient from '../api/client'
import type { User } from '../types'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setIsLoading(false)
      return
    }
    apiClient
      .get<User>('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem('access_token')
      })
      .finally(() => setIsLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const res = await apiClient.post<{ access_token: string }>('/auth/login', {
      email,
      password,
    })
    localStorage.setItem('access_token', res.data.access_token)
    const meRes = await apiClient.get<User>('/auth/me')
    setUser(meRes.data)
    localStorage.setItem('user', JSON.stringify(meRes.data))
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: !!user, isLoading, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
