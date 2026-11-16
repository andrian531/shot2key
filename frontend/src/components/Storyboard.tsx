import { useEffect, useState } from 'react'
import type {
  Character,
  Engine,
  ImageEngine,
  Project,
  SceneCharacterMapping,
  SystemStatus,
} from '../types'
import { formatBytes, formatTime } from '../lib/format'
import SceneCard from './SceneCard'

interface Props {
  project: Project
  characters: Character[]
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
  onUpdateSceneCharacters: (
    sceneId: string,
    replaceCharacters: boolean,
    mappings: Record<string, SceneCharacterMapping>,
  ) => Promise<void>
  onApplyCharactersAll: (mappings: Record<string, SceneCharacterMapping>) => Promise<void>
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
  characters,
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
  onUpdateSceneCharacters,
  onApplyCharactersAll,
  onExport,
}: Props) {
  const scenes = [...(project.scenes ?? [])].sort((a, b) => a.start_time - b.start_time)
  const [selectedId, setSelectedId] = useState<string | null>(scenes[0]?.id ?? null)

  useEffect(() => {
    if (scenes.length === 0) {
      setSelectedId(null)
      return
    }
    if (!selectedId || !scenes.some((s) => s.id === selectedId)) {
      setSelectedId(scenes[0].id)
    }
  }, [scenes, selectedId])

  const selectedIndex = scenes.findIndex((s) => s.id === selectedId)
  const activeScene = selectedIndex >= 0 ? scenes[selectedIndex] : scenes[0]

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

        {analyzing && (
          <div className="mt-3">
            <div className="mb-1 flex items-center justify-between text-[11px] text-indigo-300">
              <span>
                ⏳ Menganalisis &amp; membuat prompt otomatis ({project.analysis?.done ?? 0}/
                {project.analysis?.total ?? scenes.length} scene) dengan{' '}
                {project.analysis?.engine ?? analyzer}...
              </span>
              <span className="font-mono">
                {Math.round(
                  ((project.analysis?.done ?? 0) /
                    Math.max(1, project.analysis?.total ?? scenes.length)) *
                    100,
                )}
                %
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-800">
              <div
                className="h-full animate-pulse rounded-full bg-indigo-500 transition-all duration-500"
                style={{
                  width: `${Math.max(
                    8,
                    Math.round(
                      ((project.analysis?.done ?? 0) /
                        Math.max(1, project.analysis?.total ?? scenes.length)) *
                        100,
                    ),
                  )}%`,
                }}
              />
            </div>
          </div>
        )}

        {generating && (
          <div className="mt-3">
            <div className="mb-1 flex items-center justify-between text-[11px] text-emerald-300">
              <span>
                🎨 Menggenerate keyframe ({project.generation?.done ?? 0}/
                {project.generation?.queued ?? scenes.length}) dengan{' '}
                {project.generation?.engine ?? imageEngine}...
              </span>
              <span className="font-mono">
                {Math.round(
                  ((project.generation?.done ?? 0) /
                    Math.max(1, project.generation?.queued ?? scenes.length)) *
                    100,
                )}
                %
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-800">
              <div
                className="h-full animate-pulse rounded-full bg-emerald-500 transition-all duration-500"
                style={{
                  width: `${Math.max(
                    8,
                    Math.round(
                      ((project.generation?.done ?? 0) /
                        Math.max(1, project.generation?.queued ?? scenes.length)) *
                        100,
                    ),
                  )}%`,
                }}
              />
            </div>
          </div>
        )}

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

      {scenes.length > 0 && activeScene && (
        <div className="mt-5 flex flex-col gap-5 lg:flex-row lg:items-start">
          {/* Sidebar: Timeline list of scenes by time */}
          <aside className="card w-full shrink-0 overflow-hidden lg:sticky lg:top-16 lg:w-80">
            <div className="border-b border-ink-800 px-3.5 py-2.5 text-xs font-semibold text-slate-300">
              Timeline Scene ({scenes.length})
            </div>
            <div className="max-h-[72vh] divide-y divide-ink-800/70 overflow-y-auto">
              {scenes.map((scene) => {
                const selected = scene.id === activeScene.id
                const hasPrompt = Boolean(scene.prompt.trim())
                const hasKeyframe = scene.image_status === 'done'
                return (
                  <button
                    key={scene.id}
                    type="button"
                    onClick={() => setSelectedId(scene.id)}
                    className={`flex w-full items-center gap-3 px-3 py-2.5 text-left transition ${
                      selected
                        ? 'bg-indigo-950/50 ring-1 ring-inset ring-indigo-500/40'
                        : 'hover:bg-ink-900/70'
                    }`}
                  >
                    <img
                      src={
                        hasKeyframe
                          ? `/api/projects/${project.id}/scenes/${scene.id}/image`
                          : `/api/projects/${project.id}/scenes/${scene.id}/keyframe`
                      }
                      alt={`Scene ${scene.index}`}
                      className="h-12 w-20 shrink-0 rounded bg-ink-950 object-cover"
                      loading="lazy"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <span
                          className={`text-xs font-semibold ${
                            selected ? 'text-indigo-200' : 'text-slate-200'
                          }`}
                        >
                          Scene {String(scene.index).padStart(2, '0')}
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">
                          {scene.duration.toFixed(1)}s
                        </span>
                      </div>
                      <div className="mt-0.5 font-mono text-[10px] text-slate-400">
                        {formatTime(scene.start_time)} → {formatTime(scene.end_time)}
                      </div>
                      <div className="mt-1 flex items-center gap-1.5 text-[10px]">
                        <span
                          className={`rounded px-1.5 py-0.5 ${
                            hasPrompt
                              ? 'bg-emerald-950/60 text-emerald-300'
                              : analyzing
                                ? 'bg-indigo-950/60 text-indigo-300'
                                : 'bg-ink-800 text-slate-500'
                          }`}
                        >
                          {hasPrompt ? 'prompt ✓' : analyzing ? 'antre...' : 'kosong'}
                        </span>
                        {hasKeyframe && (
                          <span className="rounded bg-emerald-950/60 px-1.5 py-0.5 text-emerald-300">
                            keyframe ✓
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </aside>

          {/* Main Workspace: Selected Scene Detail */}
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>
                Menampilkan <strong className="text-slate-200">Scene {String(activeScene.index).padStart(2, '0')}</strong>{' '}
                dari {scenes.length}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn-ghost py-1 text-xs"
                  disabled={selectedIndex <= 0}
                  onClick={() => setSelectedId(scenes[selectedIndex - 1]?.id ?? null)}
                >
                  ← Sebelumnya
                </button>
                <button
                  type="button"
                  className="btn-ghost py-1 text-xs"
                  disabled={selectedIndex < 0 || selectedIndex >= scenes.length - 1}
                  onClick={() => setSelectedId(scenes[selectedIndex + 1]?.id ?? null)}
                >
                  Berikutnya →
                </button>
              </div>
            </div>

            <SceneCard
              key={activeScene.id}
              projectId={project.id}
              scene={activeScene}
              characters={characters}
              analyzing={analyzing}
              engine={sceneEngines[activeScene.id] ?? imageEngine}
              onEngineChange={(engine) => onSceneEngineChange(activeScene.id, engine)}
              onSavePrompt={onSavePrompt}
              onUpdateSceneCharacters={onUpdateSceneCharacters}
              onApplyCharactersAll={onApplyCharactersAll}
              onGenerate={onGenerateScene}
              keyframeUrl={`/api/projects/${project.id}/scenes/${activeScene.id}/keyframe`}
              imageUrl={`/api/projects/${project.id}/scenes/${activeScene.id}/image`}
            />
          </div>
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
