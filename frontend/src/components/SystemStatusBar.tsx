import type { SystemStatus } from '../types'

interface Props {
  status: SystemStatus | null
  onOpenSettings: () => void
}

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`h-1.5 w-1.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-rose-500'}`}
      aria-hidden
    />
  )
}

function Pill({
  label,
  ok,
  title,
}: {
  label: string
  ok: boolean
  title?: string
}) {
  return (
    <span
      className={`pill ${ok ? 'text-slate-200' : 'border-rose-900/60 text-rose-300'}`}
      title={title}
    >
      <Dot ok={ok} />
      {label}
    </span>
  )
}

export default function SystemStatusBar({ status, onOpenSettings }: Props) {
  const rea = status?.rea_video
  const ffmpeg = status?.ffmpeg
  const agy = status?.agy
  const codex = status?.codex

  return (
    <header className="sticky top-0 z-20 border-b border-ink-800 bg-ink-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-3 px-5 py-3">
        <div className="flex items-center gap-2.5">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            S2K
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-strong">Shot2Key</div>
            <div className="text-[11px] text-slate-500">Storyboard &amp; keyframe studio</div>
          </div>
        </div>

        <div className="ml-2 flex flex-wrap items-center gap-1.5">
          <Pill
            label={`rea-video${rea?.version ? ` ${rea.version}` : ''}`}
            ok={Boolean(rea?.available)}
            title={rea?.command ?? 'rea-video tidak ditemukan di .venv'}
          />
          <Pill
            label={`ffmpeg${ffmpeg?.source ? ` (${ffmpeg.source})` : ''}`}
            ok={Boolean(ffmpeg?.available)}
            title={ffmpeg?.path ?? 'ffmpeg tidak ditemukan'}
          />
          <Pill label="agy" ok={Boolean(agy?.available)} title={agy?.path ?? 'agy CLI tidak ditemukan'} />
          <Pill
            label="codex"
            ok={Boolean(codex?.available)}
            title={codex?.path ?? 'codex CLI tidak ditemukan'}
          />
        </div>

        <div className="ml-auto flex items-center gap-2">
          {status && !status.ready && (
            <span className="badge bg-amber-950/60 text-amber-300">
              Dependensi belum lengkap
            </span>
          )}
          <button className="btn-ghost" onClick={onOpenSettings}>
            Settings
          </button>
        </div>
      </div>
    </header>
  )
}
