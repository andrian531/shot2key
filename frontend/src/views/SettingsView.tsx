import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Settings } from '../types'
import { useApp } from '../state/AppContext'

/** `/settings` — API keys, default engines, auto-analyze and style prompt. */
export default function SettingsView() {
  const { refreshStatus } = useApp()
  const [settings, setSettings] = useState<Settings | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Settings · Shot2Key'
    api
      .getSettings()
      .then(setSettings)
      .catch((err: Error) => setError(err.message))
  }, [])

  function update<K extends keyof Settings>(key: K, value: Settings[K]) {
    setSettings((current) => (current ? { ...current, [key]: value } : current))
  }

  async function save() {
    if (!settings) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const saved = await api.saveSettings({
        gemini_api_key: settings.gemini_api_key,
        gemini_model: settings.gemini_model,
        openai_base_url: settings.openai_base_url,
        openai_api_key: settings.openai_api_key,
        openai_model: settings.openai_model,
        default_analyzer: settings.default_analyzer,
        default_image_engine: settings.default_image_engine,
        rea_video_lang: settings.rea_video_lang,
        rea_video_vlm: settings.rea_video_vlm,
        auto_analyze: settings.auto_analyze,
        default_style_prompt: settings.default_style_prompt,
        max_scene_seconds: settings.max_scene_seconds,
      })
      setSettings(saved)
      await refreshStatus()
      setNotice('Settings tersimpan.')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-6">
      <div className="mb-4">
        <h1 className="text-lg font-semibold text-strong">Settings</h1>
        <p className="mt-0.5 text-[12px] text-slate-400">
          Engine CLI default, durasi scene, dan perilaku otomatis. Disimpan lokal di{' '}
          <code className="text-slate-300">backend/data/settings.json</code>.
        </p>
      </div>

      {!settings ? (
        <div className="card p-6 text-sm text-slate-400">
          {error ? `Gagal memuat settings: ${error}` : 'Memuat...'}
        </div>
      ) : (
        <div className="space-y-4">
          {/* API Provider UI sementara disembunyikan sampai pengujian API key selesai.
              Backend (gemini / openai) tetap aktif dan siap dipakai nanti. */}
          {/* <section className="card space-y-4 p-5">
            <h2 className="text-sm font-semibold text-strong">API Provider</h2>

            <div>
              <label className="label">Gemini API key</label>
              <input
                className="input"
                type="password"
                placeholder={settings.gemini_api_key_set ? '•••••• (tersimpan)' : 'belum diisi'}
                value={settings.gemini_api_key}
                onChange={(event) => update('gemini_api_key', event.target.value)}
              />
              <div className="mt-1.5 flex items-center gap-2">
                <span className="text-[11px] text-slate-500">model</span>
                <input
                  className="input py-1 text-xs"
                  value={settings.gemini_model}
                  onChange={(event) => update('gemini_model', event.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="label">OpenAI-compatible endpoint</label>
              <input
                className="input"
                value={settings.openai_base_url}
                onChange={(event) => update('openai_base_url', event.target.value)}
              />
              <div className="mt-1.5 grid grid-cols-2 gap-2">
                <input
                  className="input py-1 text-xs"
                  type="password"
                  placeholder={settings.openai_api_key_set ? '•••••• (tersimpan)' : 'API key'}
                  value={settings.openai_api_key}
                  onChange={(event) => update('openai_api_key', event.target.value)}
                />
                <input
                  className="input py-1 text-xs"
                  value={settings.openai_model}
                  onChange={(event) => update('openai_model', event.target.value)}
                />
              </div>
            </div>
          </section> */}

          <section className="card space-y-4 p-5">
            <h2 className="text-sm font-semibold text-strong">Engine Default</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Analyzer default</label>
                <select
                  className="input"
                  value={settings.default_analyzer}
                  onChange={(event) =>
                    update('default_analyzer', event.target.value as Settings['default_analyzer'])
                  }
                >
                  <option value="agy">agy</option>
                  <option value="codex">codex</option>
                  {/* Aktifkan kembali setelah pengujian API key selesai:
                  <option value="gemini">gemini</option>
                  <option value="openai">openai</option>
                  */}
                </select>
              </div>
              <div>
                <label className="label">Image engine default</label>
                <select
                  className="input"
                  value={settings.default_image_engine}
                  onChange={(event) =>
                    update(
                      'default_image_engine',
                      event.target.value as Settings['default_image_engine'],
                    )
                  }
                >
                  <option value="agy">agy</option>
                  <option value="codex">codex</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Max durasi scene (detik)</label>
                <select
                  className="input"
                  value={String(settings.max_scene_seconds ?? 10)}
                  onChange={(event) => update('max_scene_seconds', Number(event.target.value))}
                >
                  <option value="5">5 detik</option>
                  <option value="8">8 detik</option>
                  <option value="10">10 detik</option>
                </select>
                <p className="mt-1 text-[11px] text-slate-500">
                  Shot tidak pernah digabung; shot lebih panjang dari ini akan dipecah.
                </p>
              </div>
              <div>
                <label className="label">Bahasa laporan rea-video</label>
                <select
                  className="input"
                  value={settings.rea_video_lang}
                  onChange={(event) => update('rea_video_lang', event.target.value)}
                >
                  <option value="en">English</option>
                  <option value="zh">中文</option>
                </select>
              </div>
              <label className="flex items-end gap-2 pb-2 text-xs text-slate-400">
                <input
                  type="checkbox"
                  checked={settings.rea_video_vlm}
                  onChange={(event) => update('rea_video_vlm', event.target.checked)}
                />
                Pakai VLM (butuh API key Gemini di env)
              </label>
            </div>
          </section>

          <section className="card space-y-3 p-5">
            <h2 className="text-sm font-semibold text-strong">Otomatisasi &amp; Gaya</h2>
            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={Boolean(settings.auto_analyze)}
                onChange={(event) => update('auto_analyze', event.target.checked)}
              />
              Auto-Analyze &amp; buat prompt otomatis setelah video selesai dipecah
            </label>
            <div>
              <label className="label">Default Style Prompt (otomatis ditambahkan saat generate)</label>
              <textarea
                className="input min-h-[80px] resize-y font-mono text-xs"
                value={settings.default_style_prompt ?? ''}
                onChange={(event) => update('default_style_prompt', event.target.value)}
              />
            </div>
          </section>

          {error && (
            <p className="rounded border border-rose-900/60 bg-rose-950/40 px-3 py-2 text-xs text-rose-300">
              {error}
            </p>
          )}
          {notice && (
            <p className="rounded border border-emerald-900/60 bg-emerald-950/40 px-3 py-2 text-xs text-emerald-300">
              {notice}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <button className="btn-primary" disabled={saving} onClick={save}>
              {saving ? 'Menyimpan...' : 'Simpan Settings'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
