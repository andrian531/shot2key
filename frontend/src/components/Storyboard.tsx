import type { Engine, ImageEngine, Project, SystemStatus } from '../types'
import { formatBytes, formatTime } from '../lib/format'
import SceneCard from './SceneCard'

interface Props {
  project: Project
  status: SystemStatus | null
  analyzer: Engine
  imageEngine: ImageEngine
  sceneEngines: Record<string, ImageEngine>
  busy: boolean
  error: string | null
  onBack: () => void
  onAnalyzerChange: (engine: Engine) => void
  onImageEngineChange: (engine: ImageEngine) => void
  onSceneEngineChange: (sceneId: string, engine: ImageEngine) => void
  onAnalyze: () => void
  onGenerateAll: () => void
  onGenerateScene: (sceneId: string) => void
  onSavePrompt: (sceneId: string, prompt: string) => Promise<void>
  onExport: () => void
}

function Progress({ project }: { project: Project }) {
  const percent = project.progress?.percent ?? 0
  return (
    <div className="mt-3">
      <div className="mb-1 flex items-center justify-between text-[11px] text-slate-400">
        <span>{project.progress?.message || project.progress?.stage}</span>
        <span className="font-mono">{percent}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-800">
        <div
          className="h-full rounded-full bg-indigo-500 transition-all duration-500"
          style={{ width: `${Math.max(2, percent)}%` }}
        />
      </div>
    </div>
  )
}

export default function Storyboard({
  project,
  status,
  analyzer,
  imageEngine,
  sceneEngines,
  busy,
  error,
  onBack,
  onAnalyzerChange,
  onImageEngineChange,
  onSceneEngineChange,
  onAnalyze,
  onGenerateAll,
  onGenerateScene,
  onSavePrompt,
  onExport,
}: Props) {
  const scenes = project.scenes ?? []
  const analyzing = project.analysis?.status === 'running'
  const generating = project.generation?.status === 'running'
  const ready = project.status === 'ready'
  const withPrompt = scenes.filter((scene) => scene.prompt.trim()).length
  const withImage = scenes.filter((scene) => scene.image_status === 'done').length

  return (
    <div className="mx-auto max-w-[1600px] px-5 py-6">
      <div className="card p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <button className="mb-1 text-[11px] text-slate-500 hover:text-slate-300" onClick={onBack}>
              ← semua project
            </button>
            <h1 className="truncate text-lg font-semibold text-strong">{project.filename}</h1>
            <p className="mt-0.5 text-[12px] text-slate-500">
              {formatTime(project.source?.duration)} · {project.source?.width}×
              {project.source?.height} · {project.source?.fps} fps ·{' '}
              {formatBytes(project.size_bytes)} · {project.shots.length} shot →{' '}
              <span className="text-slate-300">{scenes.length} scene</span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-slate-500">Analyzer</span>
              <select
                className="input w-auto py-1.5 text-xs"
                value={analyzer}
                onChange={(event) => onAnalyzerChange(event.target.value as Engine)}
              >
                {(status?.engines.analyzers ?? ['agy', 'codex', 'gemini', 'openai']).map((engine) => (
                  <option key={engine} value={engine}>
                    {engine}
                    {status && !status.analyzers_ready?.[engine] ? ' (belum siap)' : ''}
                  </option>
                ))}
              </select>
              <button
                className="btn-ghost py-1.5 text-xs"
                disabled={!ready || analyzing || busy}
                onClick={onAnalyze}
              >
                {analyzing ? 'Menganalisis...' : 'Analyze'}
              </button>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-slate-500">Image</span>
              <select
                className="input w-auto py-1.5 text-xs"
                value={imageEngine}
                onChange={(event) => onImageEngineChange(event.target.value as ImageEngine)}
              >
                <option value="agy">agy</option>
                <option value="codex">codex</option>
              </select>
              <button
                className="btn-primary py-1.5 text-xs"
                disabled={!ready || generating || withPrompt === 0}
                onClick={onGenerateAll}
              >
                {generating ? 'Generating...' : `Generate All (${withPrompt})`}
              </button>
            </div>

            <button className="btn-ghost py-1.5 text-xs" disabled={!scenes.length} onClick={onExport}>
              ⬇ Export ZIP
            </button>
          </div>
        </div>

        {project.status === 'decomposing' && <Progress project={project} />}

        {project.status === 'failed' && (
          <p className="mt-3 rounded-lg border border-rose-900/60 bg-rose-950/40 px-3 py-2 text-xs text-rose-300">
            Decompose gagal: {project.error}
          </p>
        )}

        {error && (
          <p className="mt-3 rounded-lg border border-rose-900/60 bg-rose-950/40 px-3 py-2 text-xs text-rose-300">
            {error}
          </p>
        )}

        {ready && (
          <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
            <span>
              prompt: <span className="text-slate-300">{withPrompt}</span>/{scenes.length}
            </span>
            <span>
              keyframe: <span className="text-slate-300">{withImage}</span>/{scenes.length}
            </span>
            {project.analysis?.status === 'running' && (
              <span className="text-indigo-300">
                analyze {project.analysis.done ?? 0}/{project.analysis.total ?? scenes.length}
              </span>
            )}
            {project.analysis?.status === 'partial' && (
              <span className="text-amber-300">sebagian scene gagal dianalisis</span>
            )}
            {project.generation?.status === 'running' && (
              <span className="text-indigo-300">
                generate {project.generation.done}/{project.generation.queued}
              </span>
            )}
            {project.generation?.status === 'partial' && (
              <span className="text-amber-300">
                {project.generation.failed} keyframe gagal
              </span>
            )}
            {project.subtitles?.srt && <span className="text-emerald-400">subtitle .srt tersedia</span>}
          </div>
        )}
      </div>

      {scenes.length > 0 && (
        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {scenes.map((scene) => (
            <SceneCard
              key={scene.id}
              projectId={project.id}
              scene={scene}
              engine={sceneEngines[scene.id] ?? imageEngine}
              onEngineChange={(engine) => onSceneEngineChange(scene.id, engine)}
              onSavePrompt={onSavePrompt}
              onGenerate={onGenerateScene}
              keyframeUrl={`/api/projects/${project.id}/scenes/${scene.id}/keyframe`}
              imageUrl={`/api/projects/${project.id}/scenes/${scene.id}/image`}
            />
          ))}
        </div>
      )}

      {project.status === 'decomposing' && scenes.length === 0 && (
        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <div key={index} className="card h-64 animate-pulse bg-ink-900/60" />
          ))}
        </div>
      )}
    </div>
  )
}
