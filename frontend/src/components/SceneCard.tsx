import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Character, ImageEngine, Scene, SceneCharacterMapping } from '../types'
import { formatTime } from '../lib/format'

interface Props {
  projectId: string
  scene: Scene
  characters: Character[]
  analyzing?: boolean
  engine: ImageEngine
  onEngineChange: (engine: ImageEngine) => void
  onSavePrompt: (sceneId: string, prompt: string) => Promise<void>
  onUpdateSceneCharacters: (
    sceneId: string,
    replaceCharacters: boolean,
    mappings: Record<string, SceneCharacterMapping>,
  ) => Promise<void>
  onApplyCharactersAll: (mappings: Record<string, SceneCharacterMapping>) => Promise<void>
  onGenerate: (sceneId: string) => void
  keyframeUrl: string
  imageUrl: string
}

const STATUS_STYLE: Record<Scene['image_status'], string> = {
  idle: 'bg-ink-800 text-slate-400',
  queued: 'bg-amber-950/60 text-amber-300',
  generating: 'bg-indigo-950/70 text-indigo-300',
  done: 'bg-emerald-950/60 text-emerald-300',
  failed: 'bg-rose-950/60 text-rose-300',
}

const STATUS_LABEL: Record<Scene['image_status'], string> = {
  idle: 'belum digenerate',
  queued: 'dalam antrean',
  generating: 'menggenerate...',
  done: 'selesai',
  failed: 'gagal',
}

export default function SceneCard({
  projectId,
  scene,
  characters,
  analyzing,
  engine,
  onEngineChange,
  onSavePrompt,
  onUpdateSceneCharacters,
  onApplyCharactersAll,
  onGenerate,
  keyframeUrl,
  imageUrl,
}: Props) {
  const [prompt, setPrompt] = useState(scene.prompt)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    setPrompt(scene.prompt)
    setDirty(false)
  }, [scene.prompt])

  async function commit() {
    if (!dirty) return
    setSaving(true)
    try {
      await onSavePrompt(scene.id, prompt)
      setDirty(false)
    } finally {
      setSaving(false)
    }
  }

  const busy = scene.image_status === 'queued' || scene.image_status === 'generating'
  const hasImage = scene.image_status === 'done'
  const replaceEnabled = Boolean(scene.replace_characters)
  const mappings = scene.character_mappings ?? {}
  const detected = scene.detected_characters ?? []
  const slots =
    detected.length > 0
      ? detected
      : [{ slot: 'Char_1', description: 'Karakter utama scene ini' }]

  function handleSlotChange(slot: string, characterId: string, costumeId?: string) {
    const next = { ...mappings }
    if (!characterId) {
      delete next[slot]
    } else {
      const char = characters.find((c) => c.id === characterId)
      const defaultCostume = costumeId ?? char?.costumes?.[0]?.id ?? ''
      next[slot] = { character_id: characterId, costume_id: defaultCostume }
    }
    void onUpdateSceneCharacters(scene.id, replaceEnabled, next)
  }

  return (
    <article className="card flex flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-ink-800 px-4 py-2.5">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold text-strong">
            Scene {String(scene.index).padStart(2, '0')}
          </span>
          <span className="font-mono text-[11px] text-slate-500">
            {formatTime(scene.start_time)} → {formatTime(scene.end_time)}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="badge bg-ink-800 text-slate-400">{scene.duration.toFixed(2)}s</span>
          {scene.is_split && (
            <span className="badge bg-ink-800 text-slate-500" title="Potongan dari shot yang lebih panjang">
              split
            </span>
          )}
          <span className={`badge ${STATUS_STYLE[scene.image_status]}`}>
            {STATUS_LABEL[scene.image_status]}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-px bg-ink-800">
        <figure className="relative bg-ink-950">
          <img
            src={keyframeUrl}
            alt={`Referensi scene ${scene.index}`}
            className="aspect-video w-full object-cover"
            loading="lazy"
          />
          <figcaption className="absolute bottom-1 left-1 rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-slate-300">
            referensi
          </figcaption>
        </figure>
        <figure className="relative bg-ink-950">
          {hasImage ? (
            <img
              src={imageUrl}
              alt={`Keyframe scene ${scene.index}`}
              className="aspect-video w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="grid aspect-video w-full place-items-center text-[11px] text-slate-600">
              {busy ? 'menggenerate...' : 'belum ada keyframe'}
            </div>
          )}
          <figcaption className="absolute bottom-1 left-1 rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-slate-300">
            keyframe
          </figcaption>
        </figure>
      </div>

      <div className="flex flex-1 flex-col gap-2 p-4">
        {scene.description && (
          <p className="text-[12px] leading-relaxed text-slate-400">{scene.description}</p>
        )}
        {(scene.camera || scene.lighting) && (
          <p className="text-[11px] text-slate-500">
            {scene.camera && <span>📷 {scene.camera}</span>}
            {scene.camera && scene.lighting && <span> · </span>}
            {scene.lighting && <span>💡 {scene.lighting}</span>}
          </p>
        )}

        <div className="flex items-center justify-between">
          <label className="label mb-0 mt-1">Prompt</label>
          {analyzing && !scene.prompt.trim() && (
            <span className="animate-pulse text-[11px] text-indigo-300">
              ⏳ Menunggu analyze...
            </span>
          )}
        </div>
        <textarea
          className="input min-h-[104px] resize-y font-mono text-[12px] leading-relaxed"
          value={prompt}
          placeholder={
            analyzing
              ? 'Sedang menunggu giliran analisis AI...'
              : 'Belum ada prompt — jalankan Analyze atau tulis manual.'
          }
          onChange={(event) => {
            setPrompt(event.target.value)
            setDirty(true)
          }}
          onBlur={commit}
        />

        <div className="rounded-lg border border-ink-800 bg-ink-950/50 p-2.5">
          <div className="flex items-center justify-between gap-2">
            <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-300">
              <input
                type="checkbox"
                checked={replaceEnabled}
                onChange={(e) =>
                  void onUpdateSceneCharacters(scene.id, e.target.checked, mappings)
                }
              />
              Replace Karakter
              {detected.length > 0 && (
                <span className="badge bg-ink-800 text-[10px] text-slate-400">
                  {detected.length} terdeteksi
                </span>
              )}
            </label>
            {replaceEnabled && Object.keys(mappings).length > 0 && (
              <button
                type="button"
                className="text-[11px] text-indigo-400 hover:underline"
                onClick={() => void onApplyCharactersAll(mappings)}
                title="Terapkan pilihan karakter & kostum ini ke semua scene yang cocok"
              >
                Terapkan ke semua
              </button>
            )}
          </div>

          {replaceEnabled && (
            <div className="mt-2.5 space-y-2">
              {characters.length === 0 ? (
                <p className="text-[11px] text-slate-500">
                  Database karakter masih kosong.{' '}
                  <Link to="/characters" className="text-indigo-400 hover:underline">
                    + Tambah Karakter
                  </Link>
                </p>
              ) : (
                slots.map((item) => {
                  const current = mappings[item.slot]
                  const selectedChar = characters.find((c) => c.id === current?.character_id)
                  return (
                    <div
                      key={item.slot}
                      className="space-y-1 rounded border border-ink-800/80 bg-ink-900/50 p-2"
                    >
                      <div className="flex items-center justify-between gap-2 text-[11px]">
                        <span className="font-mono font-semibold text-indigo-300">{item.slot}</span>
                        {item.description && (
                          <span className="truncate text-slate-500" title={item.description}>
                            {item.description}
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-1.5">
                        <select
                          className="input py-1 text-xs"
                          value={current?.character_id ?? ''}
                          onChange={(e) => handleSlotChange(item.slot, e.target.value)}
                        >
                          <option value="">-- Karakter asli --</option>
                          {characters.map((char) => (
                            <option key={char.id} value={char.id}>
                              {char.name}
                            </option>
                          ))}
                        </select>
                        <select
                          className="input py-1 text-xs"
                          disabled={!selectedChar || selectedChar.costumes.length === 0}
                          value={current?.costume_id ?? ''}
                          onChange={(e) =>
                            handleSlotChange(item.slot, current?.character_id ?? '', e.target.value)
                          }
                        >
                          {!selectedChar ? (
                            <option value="">Kostum</option>
                          ) : selectedChar.costumes.length === 0 ? (
                            <option value="">(Tanpa kostum)</option>
                          ) : (
                            selectedChar.costumes.map((cos) => (
                              <option key={cos.id} value={cos.id}>
                                {cos.name}
                              </option>
                            ))
                          )}
                        </select>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          )}
        </div>

        {scene.analysis_error && (
          <p className="rounded border border-amber-900/60 bg-amber-950/40 px-2 py-1 text-[11px] text-amber-300">
            Analyze: {scene.analysis_error}
          </p>
        )}
        {scene.image_error && (
          <p className="rounded border border-rose-900/60 bg-rose-950/40 px-2 py-1 text-[11px] text-rose-300">
            {scene.image_error}
          </p>
        )}

        <div className="mt-auto flex items-center gap-2 pt-1">
          <select
            className="input w-auto py-1.5 text-xs"
            value={engine}
            onChange={(event) => onEngineChange(event.target.value as ImageEngine)}
            title="Engine untuk scene ini"
          >
            <option value="agy">agy</option>
            <option value="codex">codex</option>
          </select>
          <button
            className="btn-primary flex-1 py-1.5 text-xs"
            disabled={busy || !prompt.trim()}
            onClick={async () => {
              await commit()
              onGenerate(scene.id)
            }}
          >
            {busy ? 'Bekerja...' : hasImage ? 'Regenerate' : 'Generate Image'}
          </button>
          {saving && <span className="text-[10px] text-slate-500">menyimpan…</span>}
        </div>
        <p className="text-[10px] text-slate-600">project {projectId}</p>
      </div>
    </article>
  )
}
