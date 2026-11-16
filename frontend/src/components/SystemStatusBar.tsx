import { Link, useLocation } from 'react-router-dom'
import { useApp } from '../state/AppContext'

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`h-1.5 w-1.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-rose-500'}`}
      aria-hidden
    />
  )
}

function Pill({ label, ok, title }: { label: string; ok: boolean; title?: string }) {
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

const NAV = [
  { to: '/', label: 'Library' },
  { to: '/settings', label: 'Settings' },
]

export default function SystemStatusBar() {
  const { status } = useApp()
  const location = useLocation()

  const rea = status?.rea_video
  const ffmpeg = status?.ffmpeg
  const agy = status?.agy
  const codex = status?.codex

  // A project page belongs to the Library section.
  const inLibrary = location.pathname === '/' || location.pathname.startsWith('/projects/')

  return (
    <header className="sticky top-0 z-20 border-b border-ink-800 bg-ink-950">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-3 px-5 py-3">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-amber-500 text-xs font-bold tracking-tight text-ink-950">
            S2K
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-strong">Shot2Key</div>
            <div className="text-[11px] text-slate-400">Cutroom &amp; keyframe studio</div>
          </div>
        </Link>

        <nav className="ml-2 flex items-center gap-1" aria-label="Navigasi utama">
          {NAV.map((item) => {
            const active = item.to === '/' ? inLibrary : location.pathname === item.to
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-ink-800 text-strong'
                    : 'text-slate-300 hover:bg-ink-850 hover:text-strong'
                }`}
                aria-current={active ? 'page' : undefined}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="ml-auto flex flex-wrap items-center gap-1.5">
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
          {status && !status.ready && (
            <span className="badge bg-amber-950/60 text-amber-300">Dependensi belum lengkap</span>
          )}
        </div>
      </div>
    </header>
  )
}
