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
  { to: '/', key: 'navLibrary' as const },
  { to: '/settings', key: 'navSettings' as const },
]

export default function SystemStatusBar() {
  const { status, lang, setLang, t } = useApp()
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
            <div className="text-[11px] text-slate-400">{t.appSubtitle}</div>
          </div>
        </Link>

        <nav className="ml-2 flex items-center gap-1" aria-label={t.navAriaLabel}>
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
                {t[item.key]}
              </Link>
            )
          })}
        </nav>

        <div className="ml-auto flex flex-wrap items-center gap-1.5">
          <div
            className="mr-1 inline-flex rounded-lg border border-ink-800 bg-ink-900 p-0.5 text-[11px]"
            role="group"
            aria-label={t.langSwitchAriaLabel}
          >
            <button
              type="button"
              onClick={() => setLang('id')}
              className={`rounded px-2 py-0.5 font-medium transition-colors ${
                lang === 'id' ? 'bg-amber-500 text-ink-950' : 'text-slate-400 hover:text-strong'
              }`}
            >
              ID
            </button>
            <button
              type="button"
              onClick={() => setLang('en')}
              className={`rounded px-2 py-0.5 font-medium transition-colors ${
                lang === 'en' ? 'bg-amber-500 text-ink-950' : 'text-slate-400 hover:text-strong'
              }`}
            >
              EN
            </button>
          </div>
          <Pill
            label={`rea-video${rea?.version ? ` ${rea.version}` : ''}`}
            ok={Boolean(rea?.available)}
            title={rea?.command ?? t.reaNotFound}
          />
          <Pill
            label={`ffmpeg${ffmpeg?.source ? ` (${ffmpeg.source})` : ''}`}
            ok={Boolean(ffmpeg?.available)}
            title={ffmpeg?.path ?? t.ffmpegNotFound}
          />
          <Pill label="agy" ok={Boolean(agy?.available)} title={agy?.path ?? t.agyNotFound} />
          <Pill
            label="codex"
            ok={Boolean(codex?.available)}
            title={codex?.path ?? t.codexNotFound}
          />
          {status && !status.ready && (
            <span className="badge bg-amber-950/60 text-amber-300">{t.depsIncomplete}</span>
          )}
        </div>
      </div>
    </header>
  )
}
