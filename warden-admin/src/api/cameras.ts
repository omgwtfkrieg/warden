import { api } from './client'

export interface StreamInfo {
  width?: number
  height?: number
  codec?: string
  fps?: number
  bitrate_kbps?: number
}

export interface StreamMetadata {
  probed_at?: string
  source?: string
  main?: StreamInfo
  sub?: StreamInfo
}

export interface Camera {
  id: number
  name: string
  ip_address: string | null
  rtsp_url: string
  sub_rtsp_url: string | null
  use_ffmpeg: boolean
  use_sub_stream: boolean
  always_on: boolean
  display_order: number
  stream_path: string | null
  stream_metadata: StreamMetadata | null
  created_at: string
  updated_at: string
}

export interface CameraPayload {
  name: string
  ip_address?: string
  rtsp_url: string
  sub_rtsp_url?: string
  use_ffmpeg?: boolean
  use_sub_stream?: boolean
  always_on?: boolean
  display_order?: number
  stream_metadata?: StreamMetadata | null
}

export interface TestResult {
  reachable: boolean
  message: string
  video_codec: string | null
  audio_codec: string | null
}

export const camerasApi = {
  list: () => api.get<Camera[]>('/cameras').then((r) => r.data),
  get: (id: number) => api.get<Camera>(`/cameras/${id}`).then((r) => r.data),
  create: (data: CameraPayload) => api.post<Camera>('/cameras', data).then((r) => r.data),
  update: (id: number, data: Partial<CameraPayload>) =>
    api.put<Camera>(`/cameras/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/cameras/${id}`),
  reorder: (cameras: { id: number; display_order: number }[]) =>
    api.post('/cameras/reorder', { cameras }),
  test: (rtsp_url: string) => api.post<TestResult>('/cameras/test', { rtsp_url }).then((r) => r.data),
  probe: (id: number) => api.post<{ camera_id: number; metadata: StreamMetadata }>(`/cameras/${id}/probe`).then((r) => r.data),
  probeUrl: (rtsp_url: string) => api.post<{ metadata: StreamMetadata | null }>('/cameras/probe-url', { rtsp_url }).then((r) => r.data),
  discover: (ip: string, username: string, password: string) => api.post<{ is_reolink: boolean; main_rtsp_url: string; sub_rtsp_url: string | null; metadata: StreamMetadata | null }>('/cameras/discover', { ip, username, password }).then((r) => r.data),
}
