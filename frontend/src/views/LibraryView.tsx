import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { ProjectSummary } from '../types'
import UploadPanel from '../components/UploadPanel'
import { useApp } from '../state/AppContext'

/** `/` — every project plus the upload panel. */
export default function LibraryView() {
  const navigate = useNavigate()
  const { setError, t } = useApp()
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setLocalError] = useState<string | null>(null)

  const refreshProjects = useCallback(async () => {
    try {
      setProjects(await api.listProjects())
    } catch (err) {
      setLocalError((err as Error).message)
    }
  }, [])

  useEffect(() => {
    document.title = `${t.libraryTitle} · Shot2Key`
  }, [t.libraryTitle])

  useEffect(() => {
    void refreshProjects()
  }, [refreshProjects])

  async function handleUpload(file: File) {
    setUploading(true)
    setLocalError(null)
    try {
      const created = await api.upload(file)
      await refreshProjects()
      navigate(`/projects/${created.id}`)
    } catch (err) {
      setLocalError((err as Error).message)
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm(t.deleteProjectConfirm)) return
    try {
      await api.deleteProject(id)
      await refreshProjects()
    } catch (err) {
      setLocalError((err as Error).message)
    }
  }

  return (
    <div>
      <div className="mx-auto max-w-[1600px] px-5 pt-6">
        <h1 className="text-lg font-semibold text-strong">{t.libraryTitle}</h1>
        <p className="mt-0.5 text-[12px] text-slate-500">
          {t.librarySubtitle}
        </p>
      </div>
      <UploadPanel
        projects={projects}
        uploading={uploading}
        error={error}
        onUpload={handleUpload}
        onOpen={(id) => {
          setError(null)
          navigate(`/projects/${id}`)
        }}
        onDelete={handleDelete}
      />
    </div>
  )
}
