import type {
  Character,
  Costume,
  Project,
  ProjectSummary,
  SceneCharacterMapping,
  Settings,
  SystemStatus,
} from '../types'

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

  patchScene: (
    id: string,
    sceneId: string,
    patch: {
      prompt?: string
      description?: string
      camera?: string
      lighting?: string
      replace_characters?: boolean
      character_mappings?: Record<string, SceneCharacterMapping>
    },
  ) =>
    request<Project>(`/projects/${id}/scenes/${sceneId}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),

  applyCharacters: (
    id: string,
    character_mappings: Record<string, SceneCharacterMapping>,
    replace_characters = true,
  ) =>
    request<Project>(`/projects/${id}/apply-characters`, {
      method: 'POST',
      body: JSON.stringify({ character_mappings, replace_characters }),
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

  listCharacters: () =>
    request<{ characters: Character[] }>('/characters').then((data) => data.characters),

  createCharacter: (payload: {
    name: string
    appearance: string
    costumes: Array<Partial<Costume>>
  }) =>
    request<{ character: Character }>('/characters', {
      method: 'POST',
      body: JSON.stringify(payload),
    }).then((data) => data.character),

  updateCharacter: (
    charId: string,
    payload: { name?: string; appearance?: string; costumes?: Array<Partial<Costume>> },
  ) =>
    request<{ character: Character }>(`/characters/${charId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }).then((data) => data.character),

  deleteCharacter: (charId: string) => request<null>(`/characters/${charId}`, { method: 'DELETE' }),

  async uploadCharacterImage(charId: string, file: File): Promise<Character> {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`${BASE}/characters/${charId}/image`, {
      method: 'POST',
      body: form,
    })
    if (!response.ok) throw new Error(await parseError(response))
    const data = (await response.json()) as { character: Character }
    return data.character
  },

  characterImageUrl: (charId: string) => `${BASE}/characters/${charId}/image`,
}
