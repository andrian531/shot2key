import type { Character, Scene } from '../types'

/** Slots actively kept as `[Char_N]` when Replace Karakter is enabled. */
export function activeReplaceSlots(scene: Scene): string[] {
  if (Array.isArray(scene.replace_slots)) return scene.replace_slots
  return (scene.detected_characters ?? []).map((item) => item.slot).filter(Boolean)
}

/**
 * Replace `[Char_N]` with natural descriptions for any slot that is unchecked
 * (or when `replace_characters` is OFF), while keeping checked `[Char_N]` tags.
 */
export function formatPromptForMode(
  text: string,
  scene: Scene,
  characters: Character[] = [],
): string {
  if (!text.trim()) return text

  const keep = scene.replace_characters ? new Set(activeReplaceSlots(scene)) : new Set<string>()
  let out = text
  for (const item of scene.detected_characters ?? []) {
    const slot = item.slot?.trim()
    const desc = item.description?.trim()
    if (!slot || !desc || keep.has(slot)) continue
    out = out.split(`[${slot}]`).join(desc)
  }

  if (!scene.replace_characters) return out
  return resolveVideoPrompt(out, scene, characters, keep)
}

export function resolveVideoPrompt(
  text: string,
  scene: Scene,
  characters: Character[],
  keepSlots?: Set<string>,
): string {
  if (!text.trim() || !scene.replace_characters) return text

  const active = keepSlots ?? new Set(activeReplaceSlots(scene))
  const mappings = scene.character_mappings ?? {}
  let out = text
  const notes: string[] = []

  for (const [slot, mapping] of Object.entries(mappings)) {
    if (!active.has(slot)) continue
    const character = characters.find((item) => item.id === mapping.character_id)
    if (!character) continue

    const costume = character.costumes.find((item) => item.id === mapping.costume_id)
    const parts = [character.name]
    if (character.appearance) parts.push(character.appearance)
    if (costume) parts.push(`wearing ${costume.description || costume.name}`)
    const replacement = parts.join(', ')

    const tag = `[${slot}]`
    if (out.includes(tag)) {
      out = out.split(tag).join(replacement)
    } else {
      notes.push(`Replace ${slot} with: ${replacement}.`)
    }
  }

  return notes.length > 0 ? `${notes.join(' ')} ${out}` : out
}
