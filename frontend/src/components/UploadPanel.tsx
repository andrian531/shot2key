import { useRef, useState } from 'react'
import { useApp } from '../state/AppContext'
import type { ProjectSummary } from '../types'
import { formatTime } from '../lib/format'

interface Props {
  projects: ProjectSummary[]
  uploading: boolean
  error: string | null
  onUpload: (file: File) => void
  onOpen: (id: string) => void
  onDelete: (id: string) => void
}

const ACCEPT = '.mp4,.mov,.mkv'

export default function UploadPanel({
  projects,
  uploading,
  error,
  onUpload,
  onOpen,
  onDelete,
}: Props) {
  const { t } = useApp()
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleFiles(files: FileList | null) {
    const file = files?.[0]
    if (file) onUpload(file)
  }

  return (
    <div className="mx-auto grid max-w-[1600px] gap-6 px-5 py-8 lg:grid-cols-[1.4fr_1fr]">
      <section
        className={`card flex min-h-[320px] flex-col items-center justify-center gap-4 border-dashed p-10 text-center transition-colors ${
          dragging ? 'border-amber-500 bg-amber-950/20' : ''
        }`}
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          handleFiles(event.dataTransfer.files)
        }}
      >
        <div className="grid h-14 w-14 place-items-center rounded-xl border border-ink-700 bg-ink-850 text-amber-400">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            className="h-7 w-7"
            aria-hidden="true"
          >
            <rect x="3" y="5" width="18" height="14" rx="2" />
            <path d="M7 5v14M17 5v14M3 10h4M17 10h4M3 14h4M17 14h4" />
          </svg>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-strong">{t.dropVideoTitle}</h2>
          <p className="mt-1 text-sm text-slate-300">
            {t.dropVideoDesc}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="btn-primary"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            {uploading ? t.uploading : t.chooseFile}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(event) => handleFiles(event.target.files)}
          />
        </div>
        {error && (
          <p className="max-w-lg rounded-lg border border-rose-900/60 bg-rose-950/40 px-3 py-2 text-xs text-rose-300">
            {error}
          </p>
        )}
      </section>

      <section className="card p-5">
        <h3 className="mb-3 text-sm font-semibold text-strong">{t.recentProjects}</h3>
        {projects.length === 0 ? (
          <p className="text-sm text-slate-500">{t.noProjects}</p>
        ) : (
          <ul className="space-y-2">
            {projects.map((project) => (
              <li
                key={project.id}
                className="flex items-center gap-3 rounded-lg border border-ink-800 bg-ink-850 px-3 py-2"
              >
                <button className="min-w-0 flex-1 text-left" onClick={() => onOpen(project.id)}>
                  <div className="truncate text-sm text-slate-200">{project.filename}</div>
                  <div className="text-[11px] text-slate-500">
                    {project.scene_count} {t.sceneUnit}
                    {project.duration ? ` · ${formatTime(project.duration)}` : ''} ·{' '}
                    {project.status}
                  </div>
                </button>
                <button
                  type="button"
                  className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-rose-950/50 hover:text-rose-300"
                  onClick={() => onDelete(project.id)}
                  title={t.deleteProjectTitle}
                  aria-label={t.deleteProjectTitle}
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="h-4 w-4"
                    aria-hidden="true"
                  >
                    <path d="M3 6h18" />
                    <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                    <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                    <line x1="10" y1="11" x2="10" y2="17" />
                    <line x1="14" y1="11" x2="14" y2="17" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-[11px] leading-relaxed text-slate-500">
          {t.localStorageNote}
        </p>
      </section>
    </div>
  )
}

