import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Engine, Project, SceneCharacterMapping } from '../types'
import Storyboard from '../components/Storyboard'
import { useApp } from '../state/AppContext'

const POLL_MS = 1500

function needsPolling(project: Project | null): boolean {
  if (!project) return false
  const anySceneBusy = (project.scenes ?? []).some(
    (scene) => scene.deep_analyzing || scene.video_prompt_generating,
  )
  return (
    project.status === 'decomposing' ||
    project.status === 'uploaded' ||
    project.analysis?.status === 'running' ||
    anySceneBusy
  )
}

/** `/projects/:id` — one project's storyboard. Reloading the URL reopens it. */
export default function ProjectView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { status, characters, t } = useApp()

  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [analyzer, setAnalyzer] = useState<Engine>('agy')
  const [busy, setBusy] = useState(false)
  const [error, setLocalError] = useState<string | null>(null)
  const timer = useRef<number | null>(null)

  const refreshProject = useCallback(async (projectId: string) => {
    try {
      setProject(await api.getProject(projectId))
      setNotFound(false)
    } catch (err) {
      const message = (err as Error).message
      if (message.startsWith('404')) setNotFound(true)
      else setLocalError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Defaults come from the settings the backend reports.
  useEffect(() => {
    if (!status) return
    setAnalyzer((current) => status.defaults?.analyzer ?? current)
  }, [status])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setLocalError(null)
    void refreshProject(id)
  }, [id, refreshProject])

  useEffect(() => {
    if (project) document.title = `${project.filename} · Shot2Key`
  }, [project])

  // Poll while a job is running so progress and new keyframes appear.
  useEffect(() => {
    if (!needsPolling(project) || !project) {
      if (timer.current) {
        window.clearInterval(timer.current)
        timer.current = null
      }
      return
    }
    const projectId = project.id
    timer.current = window.setInterval(() => {
      void refreshProject(projectId)
    }, POLL_MS)
    return () => {
      if (timer.current) {
        window.clearInterval(timer.current)
        timer.current = null
      }
    }
  }, [project, refreshProject])

  async function runAction(action: () => Promise<unknown>) {
    if (!project) return
    setBusy(true)
    setLocalError(null)
    try {
      await action()
      await refreshProject(project.id)
    } catch (err) {
      setLocalError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (notFound) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-16 text-center">
        <h1 className="text-lg font-semibold text-strong">{t.projectNotFound}</h1>
        <p className="mt-1 text-sm text-slate-500">
          <code className="text-slate-400">{id}</code> — {t.projectNotFoundDesc}
        </p>
        <Link to="/" className="btn-primary mt-5 inline-flex">
          {t.backToLibrary}
        </Link>
      </div>
    )
  }

  if (loading || !project) {
    return (
      <div className="mx-auto max-w-[1600px] px-5 py-6">
        <div className="card h-28 animate-pulse bg-ink-900/60" />
        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <div key={index} className="card h-64 animate-pulse bg-ink-900/60" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <Storyboard
      project={project}
      characters={characters}
      status={status}
      analyzer={analyzer}
      busy={busy}
      error={error}
      onBack={() => navigate('/')}
      onAnalyzerChange={setAnalyzer}
      onAnalyze={() => runAction(() => api.analyze(project.id, analyzer))}
      onDeepAnalyze={(sceneId) =>
        runAction(() => api.deepAnalyzeScene(project.id, sceneId, analyzer))
      }
      onGenerateVideoPrompt={(sceneId, model) =>
        runAction(() => api.generateVideoPrompt(project.id, sceneId, model, analyzer))
      }
      onSavePrompt={(sceneId, patch) =>
        api.patchScene(project.id, sceneId, patch).then(setProject)
      }
      onUpdateSceneCharacters={(sceneId, replaceCharacters, mappings, replaceSlots) =>
        api
          .patchScene(project.id, sceneId, {
            replace_characters: replaceCharacters,
            ...(replaceSlots !== undefined ? { replace_slots: replaceSlots } : {}),
            character_mappings: mappings,
          })
          .then(setProject)
      }
      onApplyCharactersAll={(mappings: Record<string, SceneCharacterMapping>) =>
        api.applyCharacters(project.id, mappings, true).then(setProject)
      }
      onExport={() => window.open(api.exportUrl(project.id), '_blank')}
    />
  )
}
