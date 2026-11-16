import type { Character, Scene } from '../types'

/**
 * Replace `[Char_N]` with natural descriptions when `replace_characters` is OFF,
 * or keep `[Char_N]` tags (or mapped characters) when `replace_characters` is ON.
 */
export function formatPromptForMode(
  text: string,
  scene: Scene,
  characters: Character[] = [],
): string {
  if (!text.trim()) return text

  if (!scene.replace_characters) {
    let natural = text
    for (const item of scene.detected_characters ?? []) {
      const slot = item.slot?.trim()
      const desc = item.description?.trim()
      if (!slot || !desc) continue
      natural = natural.split(`[${slot}]`).join(desc)
    }
    return natural
  }

  return resolveVideoPrompt(text, scene, characters)
}

export function resolveVideoPrompt(
  text: string,
  scene: Scene,
  characters: Character[],
): string {
  if (!text.trim() || !scene.replace_characters) return text

  const mappings = scene.character_mappings ?? {}
  let out = text
  const notes: string[] = []

  for (const [slot, mapping] of Object.entries(mappings)) {
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
