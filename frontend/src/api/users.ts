import apiClient from './client'
import type { User, UserRole } from '../types'

export async function changeOwnPassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiClient.patch('/users/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

// ---- Admin user management (require admin role; backend enforces 403) ----

export interface CreateUserPayload {
  full_name: string
  email: string
  password: string
  role: UserRole
}

export interface UpdateUserPayload {
  full_name?: string
  role?: UserRole
  is_active?: boolean
}

export async function listUsers(): Promise<User[]> {
  const res = await apiClient.get<User[]>('/users/')
  return res.data
}

export async function getUser(userId: string): Promise<User> {
  const res = await apiClient.get<User>(`/users/${userId}`)
  return res.data
}

export async function createUser(payload: CreateUserPayload): Promise<User> {
  const res = await apiClient.post<User>('/users/', payload)
  return res.data
}

export async function updateUser(userId: string, payload: UpdateUserPayload): Promise<User> {
  const res = await apiClient.patch<User>(`/users/${userId}`, payload)
  return res.data
}
