export type Engine = 'agy' | 'codex' | 'gemini' | 'openai'
export type ImageEngine = 'agy' | 'codex'

export interface DependencyStatus {
  available: boolean
  path?: string | null
  command?: string | null
  version?: string | null
  source?: string
}

export interface VideoModelOption {
  id: string
  label: string
  provider: string
}

export interface SystemStatus {
  ready: boolean
  rea_video: DependencyStatus
  ffmpeg: DependencyStatus
  agy: DependencyStatus
  codex: DependencyStatus
  api_keys: Record<string, boolean>
  analyzers_ready: Record<string, boolean>
  engines: { analyzers: Engine[]; image_engines: ImageEngine[] }
  video_models?: VideoModelOption[]
  defaults: { analyzer: Engine; image_engine: ImageEngine }
  max_scene_seconds: number
  python: string
  platform: string
  data_dir: string
}

export interface DetectedCharacter {
  slot: string
  description: string
}

export interface SceneCharacterMapping {
  character_id: string
  costume_id?: string
}

export interface Costume {
  id: string
  name: string
  description: string
}

export interface Character {
  id: string
  name: string
  appearance: string
  reference_image: string | null
  costumes: Costume[]
  created_at?: string
  updated_at?: string
}

export interface DeepTimelineItem {
  time: string
  action: string
  expression: string
  camera: string
  background: string
}

export interface Scene {
  id: string
  index: number
  start_time: number
  end_time: number
  duration: number
  shot_indices: number[]
  is_split: boolean
  keyframe: string | null
  last_keyframe?: string | null
  description: string
  prompt: string
  last_prompt?: string
  video_prompt?: string
  video_model?: string
  video_prompt_generating?: boolean
  camera: string
  lighting: string
  detected_characters?: DetectedCharacter[]
  deep_timeline?: DeepTimelineItem[]
  deep_analyzing?: boolean
  replace_characters?: boolean
  character_mappings?: Record<string, SceneCharacterMapping>
  engine: string | null
  image_path: string | null
  image_status: 'idle' | 'queued' | 'generating' | 'done' | 'failed'
  image_error: string | null
  last_image_path?: string | null
  last_image_status?: 'idle' | 'queued' | 'generating' | 'done' | 'failed'
  last_image_error?: string | null
  analysis_error: string | null
}

export interface PromptLogEntry {
  timestamp: string
  scene_id: string | null
  action: string
  engine: string
  input_images: string[]
  prompt_sent: string
  raw_response: string
  parsed: Record<string, unknown> | null
  duration_ms: number
  status: string
  error: string | null
}

export interface Project {
  id: string
  filename: string
  video_path: string
  size_bytes: number
  created_at: string
  updated_at: string
  status: 'uploaded' | 'decomposing' | 'ready' | 'failed'
  progress: { stage: string; percent: number; message: string }
  error: string | null
  source: { duration?: number; width?: number; height?: number; fps?: number }
  shots: Array<{ index: number; start: number; end: number; duration: number }>
  scenes: Scene[]
  analysis: { engine: string | null; status: string; error: string | null; done?: number; total?: number }
  generation: { engine: string | null; status: string; queued: number; done: number; failed: number }
  subtitles: Record<string, string>
  audio_stems?: string[]
  report?: string | null
}

export interface ProjectSummary {
  id: string
  filename: string
  status: string
  created_at: string
  updated_at: string
  scene_count: number
  duration?: number
  progress?: { stage: string; percent: number; message: string }
}

export interface Settings {
  gemini_api_key: string
  gemini_api_key_set: boolean
  gemini_model: string
  openai_base_url: string
  openai_api_key: string
  openai_api_key_set: boolean
  openai_model: string
  default_analyzer: Engine
  default_image_engine: ImageEngine
  rea_video_lang: string
  rea_video_vlm: boolean
  auto_analyze: boolean
  default_style_prompt: string
  max_scene_seconds: number
}
