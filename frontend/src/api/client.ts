import type { Project, ProjectSummary, Settings, SystemStatus } from '../types'

const BASE = '/api'

async function parseError(response: Response): Promise<string> {
  let detail = `${response.status} ${response.statusText}`
  try {
    const body = await response.json()
    if (body?.detail) {
      detail = Array.isArray(body.detail)
        ? body.detail.map((item: { msg?: string }) => item.msg ?? JSON.stringify(item)).join('; ')
        : String(body.detail)
    }
  } catch {
    /* non-JSON error body: keep the status line */
  }
  return detail
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) throw new Error(await parseError(response))
  if (response.status === 204) return null as T
  return (await response.json()) as T
}

export const api = {
  status: () => request<SystemStatus>('/system/status'),

  listProjects: () =>
    request<{ projects: ProjectSummary[] }>('/projects').then((data) => data.projects),

  getProject: (id: string) => request<Project>(`/projects/${id}`),

  async upload(file: File): Promise<Project> {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`${BASE}/projects/upload`, { method: 'POST', body: form })
    if (!response.ok) throw new Error(await parseError(response))
    return (await response.json()) as Project
  },

  analyze: (id: string, engine: string) =>
    request<{ status: string }>(`/projects/${id}/analyze`, {
      method: 'POST',
      body: JSON.stringify({ engine }),
    }),

  patchScene: (id: string, sceneId: string, patch: Record<string, string>) =>
    request<Project>(`/projects/${id}/scenes/${sceneId}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),

  generateScene: (id: string, sceneId: string, engine: string) =>
    request<{ status: string }>(`/projects/${id}/scenes/${sceneId}/generate`, {
      method: 'POST',
      body: JSON.stringify({ engine }),
    }),

  generateAll: (id: string, engine: string) =>
    request<{ status: string; count: number }>(`/projects/${id}/generate-all`, {
      method: 'POST',
      body: JSON.stringify({ engine }),
    }),

  deleteProject: (id: string) => request<null>(`/projects/${id}`, { method: 'DELETE' }),

  getSettings: () =>
    request<{ settings: Settings }>('/settings').then((data) => data.settings),

  saveSettings: (values: Partial<Settings>) =>
    request<{ settings: Settings }>('/settings', {
      method: 'PUT',
      body: JSON.stringify(values),
    }).then((data) => data.settings),

  exportUrl: (id: string) => `${BASE}/projects/${id}/export`,
  keyframeUrl: (id: string, sceneId: string) => `${BASE}/projects/${id}/scenes/${sceneId}/keyframe`,
  imageUrl: (id: string, sceneId: string) => `${BASE}/projects/${id}/scenes/${sceneId}/image`,
}
