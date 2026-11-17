import { useEffect, useState } from 'react'
import type {
  Character,
  Engine,
  Project,
  PromptLogEntry,
  SceneCharacterMapping,
  SystemStatus,
} from '../types'
import { api } from '../api/client'
import { formatBytes, formatTime } from '../lib/format'
import { useApp } from '../state/AppContext'
import SceneCard from './SceneCard'
import type { ScenePromptPatch } from './SceneCard'

interface Props {
  project: Project
  characters: Character[]
  status: SystemStatus | null
  analyzer: Engine
  busy: boolean
  error: string | null
  onBack: () => void
  onAnalyzerChange: (engine: Engine) => void
  onAnalyze: () => void
  onDeepAnalyze: (sceneId: string) => void
  onGenerateVideoPrompt: (sceneId: string, model: string) => void
  onSavePrompt: (sceneId: string, patch: ScenePromptPatch) => Promise<void>
  onUpdateSceneCharacters: (
    sceneId: string,
    replaceCharacters: boolean,
    mappings: Record<string, SceneCharacterMapping>,
    replaceSlots?: string[],
  ) => Promise<void>
  onApplyCharactersAll: (mappings: Record<string, SceneCharacterMapping>) => Promise<void>
  onExport: () => void
}

function AudioReportPanel({ project }: { project: Project }) {
  const { t } = useApp()
  const stems = project.audio_stems ?? []
  if (stems.length === 0 && !project.report) return null

  return (
    <div className="mt-3 rounded-lg border border-ink-800 bg-ink-950/60 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="mr-1 text-[11px] font-semibold uppercase tracking-wide text-slate-300">
          {t.audioReportTitle}
        </span>
        {stems.map((stem) => (
          <div
            key={stem}
            className="flex items-center gap-2 rounded border border-ink-800 bg-ink-900 px-2.5 py-1"
          >
            <span className="text-[11px] font-medium text-slate-200">{stem}</span>
            <audio
              controls
              preload="none"
              src={api.audioStemUrl(project.id, stem)}
              className="h-7 w-40"
            />
            <a
              href={api.audioStemUrl(project.id, stem, true)}
              className="text-[11px] font-medium text-amber-400 hover:underline"
              title={`Download ${stem}.wav`}
            >
              wav
            </a>
          </div>
        ))}
        {project.report && (
          <a
            href={api.reportUrl(project.id)}
            target="_blank"
            rel="noreferrer"
            className="btn-ghost py-1 text-[11px]"
          >
            {t.openReport}
          </a>
        )}
      </div>
    </div>
  )
}

function LogsPanel({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const { t } = useApp()
  const [logs, setLogs] = useState<PromptLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    api
      .logs(projectId)
      .then((items) => {
        if (alive) setLogs(items)
      })
      .catch((err: Error) => {
        if (alive) setError(err.message)
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [projectId])

  return (
    <div className="mt-3 rounded-lg border border-ink-800 bg-ink-950/80">
      <div className="flex items-center justify-between border-b border-ink-800 px-3 py-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-300">
          {t.logsTitle(logs.length)}
        </span>
        <button className="text-[11px] text-slate-400 hover:text-slate-200" onClick={onClose}>
          {t.closeBtn}
        </button>
      </div>

      {loading ? (
        <p className="p-3 text-xs text-slate-400">{t.loadingLogs}</p>
      ) : error ? (
        <p className="p-3 text-xs text-rose-300">{error}</p>
      ) : logs.length === 0 ? (
        <p className="p-3 text-xs text-slate-400">
          {t.noLogs}
        </p>
      ) : (
        <div className="max-h-[420px] divide-y divide-ink-800/70 overflow-y-auto">
          {logs.map((entry, index) => (
            <details key={`${entry.timestamp}-${index}`} className="px-3 py-2">
              <summary className="flex cursor-pointer flex-wrap items-center gap-2 text-[11px]">
                <span
                  className={`badge ${
                    entry.status === 'ok'
                      ? 'bg-emerald-950/60 text-emerald-300'
                      : 'bg-rose-950/60 text-rose-300'
                  }`}
                >
                  {entry.status}
                </span>
                <span className="font-mono text-slate-300">{entry.action}</span>
                <span className="text-slate-200">{entry.scene_id ?? '—'}</span>
                <span className="text-slate-400">{entry.engine}</span>
                <span className="font-mono text-slate-400">{entry.duration_ms} ms</span>
                <span className="ml-auto font-mono text-[11px] text-slate-400">
                  {entry.timestamp}
                </span>
              </summary>
              <div className="mt-2 space-y-2 text-[11px]">
                {entry.error && (
                  <p className="rounded border border-rose-900/60 bg-rose-950/40 px-2 py-1 text-rose-300">
                    {entry.error}
                  </p>
                )}
                {entry.input_images.length > 0 && (
                  <div>
                    <div className="label mb-1">{t.inputImagesLabel}</div>
                    <ul className="space-y-0.5 font-mono text-[11px] text-slate-300">
                      {entry.input_images.map((image) => (
                        <li key={image} className="truncate" title={image}>
                          {image}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div>
                  <div className="label mb-1">{t.promptSentLabel}</div>
                  <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded bg-ink-900 p-2 font-mono text-[11px] text-slate-200">
                    {entry.prompt_sent || '—'}
                  </pre>
                </div>
                <div>
                  <div className="label mb-1">{t.rawResponseLabel}</div>
                  <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded bg-ink-900 p-2 font-mono text-[11px] text-slate-200">
                    {entry.raw_response || '—'}
                  </pre>
                </div>
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  )
}

function Progress({ project }: { project: Project }) {
  const percent = project.progress?.percent ?? 0
  return (
    <div className="mt-3">
      <div className="mb-1 flex items-center justify-between text-[11px] text-slate-300">
        <span>{project.progress?.message || project.progress?.stage}</span>
        <span className="font-mono">{percent}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-800">
        <div
          className="h-full rounded-full bg-amber-500 transition-all duration-500"
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
  busy,
  error,
  onBack,
  onAnalyzerChange,
  onAnalyze,
  onDeepAnalyze,
  onGenerateVideoPrompt,
  onSavePrompt,
  onUpdateSceneCharacters,
  onApplyCharactersAll,
  onExport,
}: Props) {
  const { t } = useApp()
  const scenes = [...(project.scenes ?? [])].sort((a, b) => a.start_time - b.start_time)
  const [selectedId, setSelectedId] = useState<string | null>(scenes[0]?.id ?? null)
  const [logsOpen, setLogsOpen] = useState(false)

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
  const ready = project.status === 'ready'
  const withPrompt = scenes.filter((scene) => scene.prompt.trim()).length

  return (
    <div className="mx-auto max-w-[1600px] px-5 py-6">
      <div className="card p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <button className="mb-1 text-xs text-slate-400 hover:text-slate-200" onClick={onBack}>
              {t.allProjects}
            </button>
            <h1 className="truncate text-lg font-semibold text-strong">{project.filename}</h1>
            <p className="mt-0.5 text-xs text-slate-400">
              {formatTime(project.source?.duration)} · {project.source?.width}×
              {project.source?.height} · {project.source?.fps} fps ·{' '}
              {formatBytes(project.size_bytes)} · {project.shots.length} {t.shotUnit} →{' '}
              <span className="font-medium text-slate-200">{scenes.length} {t.sceneUnit}</span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-slate-400">{t.analyzerLabel}</span>
              <select
                className="input w-auto py-1.5 text-xs"
                value={analyzer}
                onChange={(event) => onAnalyzerChange(event.target.value as Engine)}
              >
                {/* Tahap awal hanya tampilkan CLI (agy / codex); gemini/openai menyusul setelah diuji */}
                {(status?.engines.analyzers ?? ['agy', 'codex'])
                  .filter((engine) => engine === 'agy' || engine === 'codex')
                  .map((engine) => (
                    <option key={engine} value={engine}>
                      {engine}
                      {status && !status.analyzers_ready?.[engine] ? ` (${t.notReady})` : ''}
                    </option>
                  ))}
              </select>
              <button
                className="btn-primary py-1.5 text-xs"
                disabled={!ready || analyzing || busy}
                onClick={onAnalyze}
              >
                {analyzing ? t.analyzingBtn : t.analyzeBtn}
              </button>
            </div>

            <button
              className="btn-ghost py-1.5 text-xs"
              onClick={() => setLogsOpen((open) => !open)}
              title={t.logsBtn}
            >
              {t.logsBtn}
            </button>

            <button className="btn-ghost py-1.5 text-xs" disabled={!scenes.length} onClick={onExport}>
              {t.exportZip}
            </button>
          </div>
        </div>

        {project.status === 'decomposing' && <Progress project={project} />}

        {ready && <AudioReportPanel project={project} />}

        {logsOpen && (
          <LogsPanel projectId={project.id} onClose={() => setLogsOpen(false)} />
        )}

        {analyzing && (
          <div className="mt-3">
            <div className="mb-1 flex items-center justify-between text-[11px] text-amber-300">
              <span>
                {t.analyzingProgress(
                  project.analysis?.done ?? 0,
                  project.analysis?.total ?? scenes.length,
                  project.analysis?.engine ?? analyzer,
                )}
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
                className="h-full animate-pulse rounded-full bg-amber-500 transition-all duration-500"
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

        {project.status === 'failed' && (
          <p className="mt-3 rounded-lg border border-rose-900/60 bg-rose-950/40 px-3 py-2 text-xs text-rose-300">
            {t.decomposeFailed(project.error ?? '')}
          </p>
        )}

        {error && (
          <p className="mt-3 rounded-lg border border-rose-900/60 bg-rose-950/40 px-3 py-2 text-xs text-rose-300">
            {error}
          </p>
        )}

        {ready && (
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-400">
            <span>
              {t.promptCountLabel}: <span className="text-slate-200">{withPrompt}</span>/{scenes.length}
            </span>
            {project.analysis?.status === 'running' && (
              <span className="text-amber-300">
                analyze {project.analysis.done ?? 0}/{project.analysis.total ?? scenes.length}
              </span>
            )}
            {project.analysis?.status === 'partial' && (
              <span className="text-amber-300">{t.partialAnalyzeWarning}</span>
            )}
            {project.subtitles?.srt && <span className="text-emerald-400">{t.subtitlesReady}</span>}
          </div>
        )}
      </div>

      {scenes.length > 0 && activeScene && (
        <div className="mt-5 flex flex-col gap-5 lg:flex-row lg:items-start">
          {/* Sidebar: Timeline list of scenes by time */}
          <aside className="card w-full shrink-0 overflow-hidden lg:sticky lg:top-16 lg:w-80">
            <div className="border-b border-ink-800 px-3.5 py-2.5 text-xs font-semibold text-slate-200">
              {t.timelineTitle(scenes.length)}
            </div>
            <div className="max-h-[72vh] divide-y divide-ink-800/70 overflow-y-auto">
              {scenes.map((scene) => {
                const selected = scene.id === activeScene.id
                const hasPrompt = Boolean(scene.prompt.trim())
                return (
                  <button
                    key={scene.id}
                    type="button"
                    onClick={() => setSelectedId(scene.id)}
                    className={`flex w-full items-center gap-3 px-3 py-2.5 text-left transition ${
                      selected
                        ? 'bg-amber-950/30 ring-1 ring-inset ring-amber-500/40'
                        : 'hover:bg-ink-850'
                    }`}
                  >
                    <img
                      src={api.keyframeUrl(project.id, scene.id)}
                      alt={`Scene ${scene.index}`}
                      className="h-12 w-20 shrink-0 rounded bg-ink-950 object-cover"
                      loading="lazy"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <span
                          className={`text-xs font-semibold ${
                            selected ? 'text-amber-200' : 'text-slate-200'
                          }`}
                        >
                          {t.sceneTitle(String(scene.index).padStart(2, '0'))}
                        </span>
                        <span className="font-mono text-[11px] text-slate-400">
                          {scene.duration.toFixed(1)}s
                        </span>
                      </div>
                      <div className="mt-0.5 font-mono text-[11px] text-slate-300">
                        {formatTime(scene.start_time)} → {formatTime(scene.end_time)}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-1 text-[10px]">
                        <span
                          className={`rounded px-1.5 py-0.5 ${
                            hasPrompt
                              ? 'bg-emerald-950/60 text-emerald-300'
                              : analyzing || scene.deep_analyzing
                                ? 'bg-amber-950/60 text-amber-300'
                                : 'bg-ink-800 text-slate-400'
                          }`}
                        >
                          {scene.deep_analyzing
                            ? t.statusDeep
                            : hasPrompt
                              ? t.statusPromptOk
                              : analyzing
                                ? t.statusQueued
                                : t.statusEmpty}
                        </span>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </aside>

          {/* Main Workspace: Selected Scene Detail */}
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span>
                {t.showingScene(activeScene.index, scenes.length)}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn-ghost py-1 text-xs"
                  disabled={selectedIndex <= 0}
                  onClick={() => setSelectedId(scenes[selectedIndex - 1]?.id ?? null)}
                >
                  {t.prevScene}
                </button>
                <button
                  type="button"
                  className="btn-ghost py-1 text-xs"
                  disabled={selectedIndex < 0 || selectedIndex >= scenes.length - 1}
                  onClick={() => setSelectedId(scenes[selectedIndex + 1]?.id ?? null)}
                >
                  {t.nextScene}
                </button>
              </div>
            </div>

            <SceneCard
              key={activeScene.id}
              projectId={project.id}
              scene={activeScene}
              characters={characters}
              videoModels={status?.video_models ?? []}
              analyzing={analyzing}
              onSavePrompt={onSavePrompt}
              onUpdateSceneCharacters={onUpdateSceneCharacters}
              onApplyCharactersAll={onApplyCharactersAll}
              onDeepAnalyze={onDeepAnalyze}
              onGenerateVideoPrompt={onGenerateVideoPrompt}
              keyframeUrl={api.keyframeUrl(project.id, activeScene.id)}
              lastKeyframeUrl={api.lastKeyframeUrl(project.id, activeScene.id)}
              clipUrl={api.sceneClipUrl(project.id, activeScene.id)}
              clipDownloadUrl={api.sceneClipUrl(project.id, activeScene.id, true)}
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
