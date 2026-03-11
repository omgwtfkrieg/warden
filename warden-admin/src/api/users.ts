import { api } from './client'

export interface Role {
  id: number
  name: string
  permissions: string[]
}

export interface User {
  id: number
  email: string
  role: Role
  is_active: boolean
  created_at: string
}

export interface UserPayload {
  email: string
  password: string
  role_id: number
}

export interface UserUpdate {
  email?: string
  role_id?: number
  is_active?: boolean
}

export const usersApi = {
  list: () => api.get<User[]>('/users').then((r) => r.data),
  roles: () => api.get<Role[]>('/users/roles').then((r) => r.data),
  create: (data: UserPayload) => api.post<User>('/users', data).then((r) => r.data),
  update: (id: number, data: UserUpdate) => api.put<User>(`/users/${id}`, data).then((r) => r.data),
  resetPassword: (id: number, password: string) =>
    api.post(`/users/${id}/reset-password`, { password }),
  remove: (id: number) => api.delete(`/users/${id}`),
}
