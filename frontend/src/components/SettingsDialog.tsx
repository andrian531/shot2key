import { useEffect, useState } from 'react'
import type { Settings } from '../types'
import { api } from '../api/client'

interface Props {
  open: boolean
  onClose: () => void
  onSaved: () => void
}

export default function SettingsDialog({ open, onClose, onSaved }: Props) {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    api
      .getSettings()
      .then(setSettings)
      .catch((err: Error) => setError(err.message))
  }, [open])

  if (!open) return null

  function update<K extends keyof Settings>(key: K, value: Settings[K]) {
    setSettings((current) => (current ? { ...current, [key]: value } : current))
  }

  async function save() {
    if (!settings) return
    setSaving(true)
    setError(null)
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
      })
      setSettings(saved)
      onSaved()
      onClose()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/70 p-4" onClick={onClose}>
      <div
        className="card w-full max-w-xl p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-strong">Settings</h2>
          <button className="text-slate-500 hover:text-slate-300" onClick={onClose}>
            ✕
          </button>
        </div>

        {!settings ? (
          <p className="text-sm text-slate-500">Memuat...</p>
        ) : (
          <div className="space-y-4">
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
                  <option value="gemini">gemini</option>
                  <option value="openai">openai</option>
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

            {error && (
              <p className="rounded border border-rose-900/60 bg-rose-950/40 px-2 py-1 text-[11px] text-rose-300">
                {error}
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button className="btn-ghost" onClick={onClose}>
                Batal
              </button>
              <button className="btn-primary" disabled={saving} onClick={save}>
                {saving ? 'Menyimpan...' : 'Simpan'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
