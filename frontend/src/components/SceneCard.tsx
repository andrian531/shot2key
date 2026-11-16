import { useEffect, useState } from 'react'
import type { Character, ImageEngine, Scene, SceneCharacterMapping } from '../types'
import { formatTime } from '../lib/format'
import { formatPromptForMode } from '../lib/prompts'

export interface ScenePromptPatch {
  prompt?: string
  last_prompt?: string
  video_prompt?: string
}

interface Props {
  projectId: string
  scene: Scene
  characters: Character[]
  analyzing?: boolean
  engine: ImageEngine
  onEngineChange: (engine: ImageEngine) => void
  onSavePrompt: (sceneId: string, patch: ScenePromptPatch) => Promise<void>
  onUpdateSceneCharacters: (
    sceneId: string,
    replaceCharacters: boolean,
    mappings: Record<string, SceneCharacterMapping>,
  ) => Promise<void>
  onApplyCharactersAll: (mappings: Record<string, SceneCharacterMapping>) => Promise<void>
  onDeepAnalyze: (sceneId: string) => void
  onGenerate: (sceneId: string, target?: 'first' | 'last' | 'both') => void
  keyframeUrl: string
  lastKeyframeUrl: string
  imageUrl: string
  lastImageUrl: string
}

const STATUS_STYLE: Record<Scene['image_status'], string> = {
  idle: 'bg-ink-800 text-slate-300',
  queued: 'bg-amber-950/60 text-amber-300',
  generating: 'bg-amber-950/70 text-amber-200',
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

function CopyButton({
  text,
  label,
  caption = 'Copy',
}: {
  text: string
  label: string
  caption?: string
}) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    if (!text.trim()) return
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      const area = document.createElement('textarea')
      area.value = text
      document.body.appendChild(area)
      area.select()
      document.execCommand('copy')
      document.body.removeChild(area)
    }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  return (
    <button
      type="button"
      className="rounded border border-ink-700 bg-ink-850 px-2.5 py-0.5 text-[11px] font-medium text-slate-200 hover:bg-ink-800 disabled:opacity-40"
      disabled={!text.trim()}
      onClick={copy}
      title={`Copy ${label}`}
    >
      {copied ? 'Copied' : caption}
    </button>
  )
}

export default function SceneCard({
  projectId,
  scene,
  characters,
  analyzing = false,
  engine,
  onEngineChange,
  onSavePrompt,
  onUpdateSceneCharacters,
  onDeepAnalyze,
  onGenerate,
  keyframeUrl,
  lastKeyframeUrl,
  imageUrl,
  lastImageUrl,
}: Props) {
  const [prompt, setPrompt] = useState(scene.prompt)
  const [lastPrompt, setLastPrompt] = useState(scene.last_prompt ?? '')
  const [videoPrompt, setVideoPrompt] = useState(scene.video_prompt ?? '')
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    setPrompt(scene.prompt)
    setLastPrompt(scene.last_prompt ?? '')
    setVideoPrompt(scene.video_prompt ?? '')
    setDirty(false)
  }, [scene.prompt, scene.last_prompt, scene.video_prompt])

  async function commit() {
    if (!dirty) return
    setSaving(true)
    try {
      await onSavePrompt(scene.id, {
        prompt,
        last_prompt: lastPrompt,
        video_prompt: videoPrompt,
      })
      setDirty(false)
    } finally {
      setSaving(false)
    }
  }

  const replaceEnabled = Boolean(scene.replace_characters)
  const detected = scene.detected_characters ?? []
  const displayFirstPrompt = formatPromptForMode(prompt, scene, characters)
  const displayLastPrompt = formatPromptForMode(lastPrompt, scene, characters)
  const displayVideoPrompt = formatPromptForMode(videoPrompt, scene, characters)

  const busyFirst = scene.image_status === 'queued' || scene.image_status === 'generating'
  const busyLast = scene.last_image_status === 'queued' || scene.last_image_status === 'generating'
  const busyAny = busyFirst || busyLast
  const hasFirstGen = scene.image_status === 'done'
  const hasLastGen = scene.last_image_status === 'done'
  const hasLastRef = Boolean(scene.last_keyframe)
  const deepBusy = Boolean(scene.deep_analyzing)
  const timeline = scene.deep_timeline ?? []

  return (
    <article className="card flex flex-col overflow-hidden" data-project={projectId}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink-800 px-4 py-3">
        <div className="flex items-baseline gap-2.5">
          <span className="text-sm font-semibold text-strong">
            Scene {String(scene.index).padStart(2, '0')}
          </span>
          <span className="font-mono text-xs text-slate-300">
            {formatTime(scene.start_time)} → {formatTime(scene.end_time)}
          </span>
          <span className="badge bg-ink-800 text-slate-200">{scene.duration.toFixed(2)}s</span>
          {scene.is_split && (
            <span className="badge bg-ink-800 text-slate-300" title="Potongan dari shot panjang">
              split
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="btn-ghost py-1 text-xs"
            disabled={deepBusy || analyzing}
            onClick={() => onDeepAnalyze(scene.id)}
            title="Ekstrak frame per 0.5 detik untuk analisis ekspresi, gestur & prompt lebih detail"
          >
            {deepBusy ? 'Deep Analyzing (0.5s)...' : 'Deep Analyze (0.5s)'}
          </button>
          <span className={`badge ${STATUS_STYLE[scene.image_status]}`}>
            First: {STATUS_LABEL[scene.image_status]}
          </span>
          {scene.last_image_status && scene.last_image_status !== 'idle' && (
            <span className={`badge ${STATUS_STYLE[scene.last_image_status]}`}>
              Last: {STATUS_LABEL[scene.last_image_status]}
            </span>
          )}
        </div>
      </div>

      {/* Visual Strip: Referensi (First & Last) + Keyframe Hasil Generate (First & Last) */}
      <div className="grid grid-cols-2 gap-px bg-ink-800 xl:grid-cols-4">
        <figure className="relative bg-ink-950">
          <img
            src={keyframeUrl}
            alt={`Referensi first frame scene ${scene.index}`}
            className="aspect-video w-full object-cover"
            loading="lazy"
          />
          <figcaption className="absolute bottom-1.5 left-1.5 rounded bg-black/80 px-2 py-0.5 text-[11px] font-medium text-slate-200">
            Referensi First
          </figcaption>
        </figure>

        <figure className="relative bg-ink-950">
          {hasLastRef ? (
            <img
              src={lastKeyframeUrl}
              alt={`Referensi last frame scene ${scene.index}`}
              className="aspect-video w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="grid aspect-video w-full place-items-center text-xs text-slate-400">
              tidak ada last frame
            </div>
          )}
          <figcaption className="absolute bottom-1.5 left-1.5 rounded bg-black/80 px-2 py-0.5 text-[11px] font-medium text-slate-200">
            Referensi Last
          </figcaption>
        </figure>

        <figure className="relative bg-ink-950">
          {hasFirstGen ? (
            <img
              src={imageUrl}
              alt={`Generated first keyframe scene ${scene.index}`}
              className="aspect-video w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="grid aspect-video w-full place-items-center text-xs text-slate-400">
              {busyFirst ? 'menggenerate first...' : analyzing || deepBusy ? 'menganalisis...' : 'belum ada keyframe'}
            </div>
          )}
          <figcaption className="absolute bottom-1.5 left-1.5 rounded bg-black/80 px-2 py-0.5 text-[11px] font-medium text-amber-300">
            Keyframe First
          </figcaption>
        </figure>

        <figure className="relative bg-ink-950">
          {hasLastGen ? (
            <img
              src={lastImageUrl}
              alt={`Generated last keyframe scene ${scene.index}`}
              className="aspect-video w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="grid aspect-video w-full place-items-center text-xs text-slate-400">
              {busyLast ? 'menggenerate last...' : 'belum ada last keyframe'}
            </div>
          )}
          <figcaption className="absolute bottom-1.5 left-1.5 rounded bg-black/80 px-2 py-0.5 text-[11px] font-medium text-amber-300">
            Keyframe Last
          </figcaption>
        </figure>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-4">
        {/* Summary & Technical Metadata (no emoji decoration) */}
        {(scene.description || scene.camera || scene.lighting) && (
          <div className="space-y-1.5 border-b border-ink-800 pb-3">
            {scene.description && (
              <p className="text-xs leading-relaxed text-slate-200">{scene.description}</p>
            )}
            {(scene.camera || scene.lighting) && (
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-300">
                {scene.camera && (
                  <span>
                    <strong className="text-slate-400">Kamera:</strong> {scene.camera}
                  </span>
                )}
                {scene.lighting && (
                  <span>
                    <strong className="text-slate-400">Cahaya:</strong> {scene.lighting}
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Deep Timeline (collapsible) */}
        {timeline.length > 0 && (
          <details className="rounded-lg border border-ink-800 bg-ink-950/70">
            <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-amber-300">
              Timeline Detail per 0.5s ({timeline.length} beat)
            </summary>
            <div className="divide-y divide-ink-800/70 border-t border-ink-800 px-3 py-1">
              {timeline.map((beat, idx) => (
                <div key={`${beat.time}-${idx}`} className="grid gap-1 py-2 text-xs md:grid-cols-[64px_1fr]">
                  <span className="font-mono text-amber-300">{beat.time}</span>
                  <div className="space-y-0.5 text-slate-200">
                    {beat.action && <div>Aksi: {beat.action}</div>}
                    {beat.expression && <div className="text-slate-300">Ekspresi: {beat.expression}</div>}
                    {(beat.camera || beat.background) && (
                      <div className="text-slate-400">
                        {beat.camera ? `Kamera: ${beat.camera}` : ''}
                        {beat.camera && beat.background ? ' · ' : ''}
                        {beat.background ? `Latar: ${beat.background}` : ''}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </details>
        )}

        {/* Replace Karakter Toggle: Natural vs [Char_N] */}
        <div className="rounded-lg border border-ink-800 bg-ink-950/60 px-3 py-2.5">
          <label className="flex cursor-pointer flex-wrap items-center gap-2 text-xs font-medium text-slate-200">
            <input
              type="checkbox"
              checked={replaceEnabled}
              onChange={(e) =>
                void onUpdateSceneCharacters(scene.id, e.target.checked, scene.character_mappings ?? {})
              }
            />
            Replace Karakter (tampilkan tag [Char_1], [Char_2] untuk manual di Google Flow)
            {detected.length > 0 && (
              <span className="badge bg-ink-800 text-[11px] text-slate-300">
                {detected.length} terdeteksi
              </span>
            )}
          </label>
          {replaceEnabled && detected.length > 0 && (
            <ul className="mt-2 space-y-1 border-t border-ink-800/80 pt-2 text-xs text-slate-300">
              {detected.map((char) => (
                <li key={char.slot} className="flex gap-2">
                  <span className="font-mono font-semibold text-amber-300">[{char.slot}]</span>
                  <span>{char.description}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* 3 Prompt Columns */}
        <div className="grid gap-4 xl:grid-cols-3">
          {/* 1. First Keyframe Prompt */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between gap-2">
              <label className="label mb-0">1. First Keyframe Prompt</label>
              <CopyButton text={displayFirstPrompt} label="first keyframe prompt" />
            </div>
            <textarea
              className="input min-h-[120px] flex-1 resize-y font-mono text-xs leading-relaxed"
              value={replaceEnabled ? prompt : displayFirstPrompt}
              placeholder={
                analyzing || deepBusy
                  ? 'Sedang menganalisis...'
                  : 'Prompt untuk gambar First Frame...'
              }
              onChange={(event) => {
                setPrompt(event.target.value)
                setDirty(true)
              }}
              onBlur={commit}
            />
          </div>

          {/* 2. Last Keyframe Prompt */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between gap-2">
              <label className="label mb-0">2. Last Keyframe Prompt</label>
              <CopyButton text={displayLastPrompt} label="last keyframe prompt" />
            </div>
            <textarea
              className="input min-h-[120px] flex-1 resize-y font-mono text-xs leading-relaxed"
              value={replaceEnabled ? lastPrompt : displayLastPrompt}
              placeholder={
                analyzing || deepBusy
                  ? 'Sedang menganalisis...'
                  : 'Prompt untuk gambar Last Frame...'
              }
              onChange={(event) => {
                setLastPrompt(event.target.value)
                setDirty(true)
              }}
              onBlur={commit}
            />
          </div>

          {/* 3. Video Prompt (Omni 1.2 Flash / Veo 3.1 Lite) */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between gap-2">
              <label className="label mb-0 text-amber-300">
                3. Video Prompt (Omni 1.2 / Veo 3.1 Lite)
              </label>
              <CopyButton text={displayVideoPrompt} label="video prompt" />
            </div>
            <textarea
              className="input min-h-[120px] flex-1 resize-y font-mono text-xs leading-relaxed"
              value={replaceEnabled ? videoPrompt : displayVideoPrompt}
              placeholder="Gerakan subjek, kamera, dan audio cue untuk Google Flow..."
              onChange={(event) => {
                setVideoPrompt(event.target.value)
                setDirty(true)
              }}
              onBlur={commit}
            />
          </div>
        </div>

        {/* Errors */}
        {scene.analysis_error && (
          <p className="rounded border border-amber-900/60 bg-amber-950/40 px-2.5 py-1.5 text-xs text-amber-300">
            Analyze: {scene.analysis_error}
          </p>
        )}
        {scene.image_error && (
          <p className="rounded border border-rose-900/60 bg-rose-950/40 px-2.5 py-1.5 text-xs text-rose-300">
            First Keyframe: {scene.image_error}
          </p>
        )}
        {scene.last_image_error && (
          <p className="rounded border border-rose-900/60 bg-rose-950/40 px-2.5 py-1.5 text-xs text-rose-300">
            Last Keyframe: {scene.last_image_error}
          </p>
        )}

        {/* Action Bar */}
        <div className="flex flex-wrap items-center gap-2 border-t border-ink-800 pt-3">
          <select
            className="input w-auto py-1.5 text-xs"
            value={engine}
            onChange={(event) => onEngineChange(event.target.value as ImageEngine)}
            title="Image Engine untuk scene ini"
          >
            <option value="agy">agy</option>
            <option value="codex">codex</option>
          </select>

          <button
            type="button"
            className="btn-ghost py-1.5 text-xs"
            disabled={!prompt.trim() || busyAny || saving}
            onClick={() => onGenerate(scene.id, 'first')}
          >
            {busyFirst ? 'Generating First...' : hasFirstGen ? 'Regenerate First' : 'Generate First'}
          </button>

          <button
            type="button"
            className="btn-ghost py-1.5 text-xs"
            disabled={!(lastPrompt.trim() || prompt.trim()) || busyAny || saving}
            onClick={() => onGenerate(scene.id, 'last')}
          >
            {busyLast ? 'Generating Last...' : hasLastGen ? 'Regenerate Last' : 'Generate Last'}
          </button>

          <button
            type="button"
            className="btn-primary ml-auto py-1.5 text-xs"
            disabled={!prompt.trim() || busyAny || saving}
            onClick={() => onGenerate(scene.id, 'both')}
          >
            {busyAny ? 'Generating...' : 'Generate Both (First + Last)'}
          </button>
        </div>
      </div>
    </article>
  )
}
