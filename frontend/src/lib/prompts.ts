import type { Character, Scene } from '../types'

/**
 * Replace `[Char_N]` placeholders in a motion prompt with the mapped character
 * and costume, mirroring `resolve_video_prompt()` on the backend.
 *
 * Returns the text unchanged when Replace Karakter is off or nothing is mapped.
 */
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
