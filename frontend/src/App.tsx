import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api/client'
import type { Engine, ImageEngine, Project, ProjectSummary, SystemStatus } from './types'
import SystemStatusBar from './components/SystemStatusBar'
import UploadPanel from './components/UploadPanel'
import Storyboard from './components/Storyboard'
import SettingsDialog from './components/SettingsDialog'

const POLL_MS = 1500

function needsPolling(project: Project | null): boolean {
  if (!project) return false
  return (
    project.status === 'decomposing' ||
    project.status === 'uploaded' ||
    project.analysis?.status === 'running' ||
    project.generation?.status === 'running'
  )
}

export default function App() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [project, setProject] = useState<Project | null>(null)
  const [analyzer, setAnalyzer] = useState<Engine>('agy')
  const [imageEngine, setImageEngine] = useState<ImageEngine>('agy')
  const [sceneEngines, setSceneEngines] = useState<Record<string, ImageEngine>>({})
  const [uploading, setUploading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const timer = useRef<number | null>(null)

  const refreshStatus = useCallback(async () => {
    try {
      const next = await api.status()
      setStatus(next)
      setAnalyzer((current) => next.defaults?.analyzer ?? current)
      setImageEngine((current) => next.defaults?.image_engine ?? current)
    } catch (err) {
      setError((err as Error).message)
    }
  }, [])

  const refreshProjects = useCallback(async () => {
    try {
      setProjects(await api.listProjects())
    } catch (err) {
      setError((err as Error).message)
    }
  }, [])

  const refreshProject = useCallback(async (id: string) => {
    try {
      setProject(await api.getProject(id))
    } catch (err) {
      setError((err as Error).message)
    }
  }, [])

  useEffect(() => {
    void refreshStatus()
    void refreshProjects()
  }, [refreshStatus, refreshProjects])

  // Poll while a job is running so progress and new keyframes appear.
  useEffect(() => {
    if (!needsPolling(project) || !project) {
      if (timer.current) {
        window.clearInterval(timer.current)
        timer.current = null
      }
      return
    }
    const id = project.id
    timer.current = window.setInterval(() => {
      void refreshProject(id)
    }, POLL_MS)
    return () => {
      if (timer.current) {
        window.clearInterval(timer.current)
        timer.current = null
      }
    }
  }, [project, refreshProject])

  async function handleUpload(file: File) {
    setUploading(true)
    setError(null)
    try {
      const created = await api.upload(file)
      setProject(created)
      setSceneEngines({})
      await refreshProjects()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm('Hapus project ini beserta videonya?')) return
    try {
      await api.deleteProject(id)
      if (project?.id === id) setProject(null)
      await refreshProjects()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function runAction(action: () => Promise<unknown>) {
    setBusy(true)
    setError(null)
    try {
      await action()
      if (project) await refreshProject(project.id)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-full pb-10">
      <SystemStatusBar status={status} onOpenSettings={() => setSettingsOpen(true)} />

      {project ? (
        <Storyboard
          project={project}
          status={status}
          analyzer={analyzer}
          imageEngine={imageEngine}
          sceneEngines={sceneEngines}
          busy={busy}
          error={error}
          onBack={() => {
            setProject(null)
            void refreshProjects()
          }}
          onAnalyzerChange={setAnalyzer}
          onImageEngineChange={setImageEngine}
          onSceneEngineChange={(sceneId, engine) =>
            setSceneEngines((current) => ({ ...current, [sceneId]: engine }))
          }
          onAnalyze={() =>
            runAction(() => api.analyze(project.id, analyzer))
          }
          onGenerateAll={() =>
            runAction(() => api.generateAll(project.id, imageEngine))
          }
          onGenerateScene={(sceneId) =>
            runAction(() =>
              api.generateScene(project.id, sceneId, sceneEngines[sceneId] ?? imageEngine),
            )
          }
          onSavePrompt={(sceneId, prompt) =>
            api.patchScene(project.id, sceneId, { prompt }).then((updated) => {
              setProject(updated)
            })
          }
          onExport={() => window.open(api.exportUrl(project.id), '_blank')}
        />
      ) : (
        <UploadPanel
          projects={projects}
          uploading={uploading}
          error={error}
          onUpload={handleUpload}
          onOpen={(id) => {
            setSceneEngines({})
            setError(null)
            void refreshProject(id)
          }}
          onDelete={handleDelete}
        />
      )}

      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={() => {
          void refreshStatus()
        }}
      />
    </div>
  )
}
