import { useRef, useState } from 'react'
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
          <h2 className="text-lg font-semibold text-strong">Drop video referensi</h2>
          <p className="mt-1 text-sm text-slate-300">
            .mp4 / .mov / .mkv — rea-video akan memecahnya per shot, lalu Shot2Key
            memisahkan scene maksimal 10 detik.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="btn-primary"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            {uploading ? 'Mengunggah...' : 'Pilih file'}
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
        <h3 className="mb-3 text-sm font-semibold text-strong">Project terakhir</h3>
        {projects.length === 0 ? (
          <p className="text-sm text-slate-500">Belum ada project.</p>
        ) : (
          <ul className="space-y-2">
            {projects.map((project) => (
              <li
                key={project.id}
                className="group flex items-center gap-3 rounded-lg border border-ink-800 bg-ink-850 px-3 py-2"
              >
                <button className="min-w-0 flex-1 text-left" onClick={() => onOpen(project.id)}>
                  <div className="truncate text-sm text-slate-200">{project.filename}</div>
                  <div className="text-[11px] text-slate-500">
                    {project.scene_count} scene
                    {project.duration ? ` · ${formatTime(project.duration)}` : ''} ·{' '}
                    {project.status}
                  </div>
                </button>
                <button
                  className="rounded px-2 py-1 text-[11px] text-slate-500 opacity-0 transition-opacity hover:text-rose-300 group-hover:opacity-100"
                  onClick={() => onDelete(project.id)}
                  title="Hapus project"
                >
                  hapus
                </button>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-[11px] leading-relaxed text-slate-500">
          Video disimpan lokal di <code className="text-slate-400">backend/uploads/</code>.
          Tidak ada upload ke cloud kecuali kamu memilih engine API.
        </p>
      </section>
    </div>
  )
}

