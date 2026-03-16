import { api } from './client'

export interface Device {
  id: number
  device_name: string | null
  device_model: string | null
  hardware_id: string | null
  platform: string | null
  paired_at: string
  last_seen_at: string | null
  revoked: boolean
}

export interface PairRequestResponse {
  code: string
  qr_payload: string
  expires_at: string
}

export interface PairStatusResponse {
  status: 'pending' | 'approved' | 'expired'
  device_token?: string
}

export const devicesApi = {
  list: () => api.get<Device[]>('/devices').then((r) => r.data),
  rename: (id: number, device_name: string) =>
    api.patch<Device>(`/devices/${id}`, { device_name }).then((r) => r.data),
  revoke: (id: number) => api.delete(`/devices/${id}`),
  delete: (id: number) => api.delete(`/devices/${id}/permanent`),
  activate: (code: string, device_name?: string) =>
    api.post('/pair/activate', { code, device_name }).then((r) => r.data),
  sendCommand: (id: number, command: 'reconnect' | 'reload' | 'refresh') =>
    api.post(`/devices/${id}/commands`, { command }).then((r) => r.data),
}
