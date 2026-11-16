import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Character, Costume } from '../types'
import { useApp } from '../state/AppContext'

interface DraftCostume {
  id?: string
  name: string
  description: string
}

const EMPTY_COSTUMES: DraftCostume[] = [{ name: 'Default', description: '' }]

/** `/characters` — character cards, reference photos and costume lists. */
export default function CharactersView() {
  const { characters, refreshCharacters } = useApp()

  const [editingId, setEditingId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [appearance, setAppearance] = useState('')
  const [costumes, setCostumes] = useState<DraftCostume[]>(EMPTY_COSTUMES)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Karakter · Shot2Key'
  }, [])

  function resetForm() {
    setEditingId(null)
    setName('')
    setAppearance('')
    setCostumes(EMPTY_COSTUMES)
    setImageFile(null)
    setError(null)
  }

  function startEdit(char: Character) {
    setEditingId(char.id)
    setName(char.name)
    setAppearance(char.appearance)
    setCostumes(
      char.costumes.length > 0
        ? char.costumes.map((c: Costume) => ({
            id: c.id,
            name: c.name,
            description: c.description,
          }))
        : EMPTY_COSTUMES,
    )
    setImageFile(null)
    setError(null)
    setNotice(null)
  }

  async function handleSave() {
    if (!name.trim()) {
      setError('Nama karakter wajib diisi.')
      return
    }
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const payload = {
        name: name.trim(),
        appearance: appearance.trim(),
        costumes: costumes.filter((c) => c.name.trim() || c.description.trim()),
      }
      const saved = editingId
        ? await api.updateCharacter(editingId, payload)
        : await api.createCharacter(payload)
      if (imageFile) {
        await api.uploadCharacterImage(saved.id, imageFile)
      }
      resetForm()
      await refreshCharacters()
      setNotice(`Karakter "${saved.name}" tersimpan.`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(charId: string) {
    if (!window.confirm('Hapus karakter ini dari database?')) return
    try {
      await api.deleteCharacter(charId)
      if (editingId === charId) resetForm()
      await refreshCharacters()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <div className="mx-auto max-w-[1600px] px-5 py-6">
      <div className="mb-4">
        <h1 className="text-lg font-semibold text-strong">Database Karakter &amp; Kostum</h1>
        <p className="mt-0.5 text-[12px] text-slate-500">
          Simpan profil karakter beserta foto referensi dan variasi kostum untuk menjaga
          konsistensi antar scene.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        {/* Form tambah / edit karakter */}
        <section className="card space-y-3 p-5">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-strong">
              {editingId ? 'Edit Karakter' : 'Tambah Karakter Baru'}
            </span>
            {editingId && (
              <button className="text-[11px] text-indigo-400 hover:underline" onClick={resetForm}>
                + Buat Baru
              </button>
            )}
          </div>

          <div>
            <label className="label">Nama Karakter</label>
            <input
              className="input"
              placeholder="Misal: Alya"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div>
            <label className="label">Ciri Fisik / Wajah (Appearance)</label>
            <textarea
              className="input min-h-[68px] resize-y text-xs"
              placeholder="Misal: young Indonesian woman, 22yo, wavy black shoulder-length hair, warm skin tone"
              value={appearance}
              onChange={(e) => setAppearance(e.target.value)}
            />
          </div>

          <div>
            <label className="label">Foto Referensi Karakter (Opsional)</label>
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.webp"
              className="block w-full text-xs text-slate-400 file:mr-3 file:rounded file:border-0 file:bg-ink-800 file:px-3 file:py-1.5 file:text-xs file:text-slate-200 hover:file:bg-ink-700"
              onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
            />
            {editingId && (
              <p className="mt-1 text-[11px] text-slate-500">
                Pilih file baru untuk mengganti foto yang tersimpan.
              </p>
            )}
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="label mb-0">Daftar Kostum</label>
              <button
                type="button"
                className="text-[11px] text-indigo-400 hover:underline"
                onClick={() => setCostumes((cur) => [...cur, { name: '', description: '' }])}
              >
                + Tambah Kostum
              </button>
            </div>
            <div className="space-y-2">
              {costumes.map((cos, idx) => (
                <div key={idx} className="rounded border border-ink-800 bg-ink-900/60 p-2">
                  <div className="mb-1.5 flex items-center gap-2">
                    <input
                      className="input py-1 text-xs"
                      placeholder="Nama kostum (misal: Streetwear)"
                      value={cos.name}
                      onChange={(e) =>
                        setCostumes((cur) =>
                          cur.map((item, i) => (i === idx ? { ...item, name: e.target.value } : item)),
                        )
                      }
                    />
                    {costumes.length > 1 && (
                      <button
                        type="button"
                        className="text-xs text-rose-400 hover:text-rose-300"
                        onClick={() => setCostumes((cur) => cur.filter((_, i) => i !== idx))}
                      >
                        Hapus
                      </button>
                    )}
                  </div>
                  <input
                    className="input py-1 text-xs"
                    placeholder="Detail kostum (misal: oversized black hoodie, cargo pants, white sneakers)"
                    value={cos.description}
                    onChange={(e) =>
                      setCostumes((cur) =>
                        cur.map((item, i) =>
                          i === idx ? { ...item, description: e.target.value } : item,
                        ),
                      )
                    }
                  />
                </div>
              ))}
            </div>
          </div>

          {error && (
            <p className="rounded border border-rose-900/60 bg-rose-950/40 px-2 py-1 text-[11px] text-rose-300">
              {error}
            </p>
          )}
          {notice && (
            <p className="rounded border border-emerald-900/60 bg-emerald-950/40 px-2 py-1 text-[11px] text-emerald-300">
              {notice}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            {editingId && (
              <button className="btn-ghost text-xs" onClick={resetForm}>
                Batal
              </button>
            )}
            <button className="btn-primary text-xs" disabled={saving} onClick={handleSave}>
              {saving ? 'Menyimpan...' : editingId ? 'Simpan Perubahan' : 'Simpan Karakter'}
            </button>
          </div>
        </section>

        {/* Daftar karakter tersimpan */}
        <section className="space-y-2.5">
          <div className="text-xs font-semibold text-slate-300">
            Karakter Tersimpan ({characters.length})
          </div>
          {characters.length === 0 ? (
            <div className="card border-dashed p-8 text-center text-xs text-slate-500">
              Belum ada karakter. Buat satu di sebelah kiri.
            </div>
          ) : (
            characters.map((char) => (
              <div key={char.id} className="card flex gap-3 p-3">
                {char.reference_image ? (
                  <img
                    src={`${api.characterImageUrl(char.id)}?t=${encodeURIComponent(char.updated_at || '')}`}
                    alt={char.name}
                    className="h-16 w-16 shrink-0 rounded-md object-cover"
                  />
                ) : (
                  <div className="grid h-16 w-16 shrink-0 place-items-center rounded-md bg-ink-800 text-xs font-semibold text-slate-400">
                    {char.name.slice(0, 2).toUpperCase()}
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-semibold text-strong">{char.name}</span>
                    <div className="flex shrink-0 gap-2 text-[11px]">
                      <button className="text-indigo-400 hover:underline" onClick={() => startEdit(char)}>
                        Edit
                      </button>
                      <button
                        className="text-rose-400 hover:underline"
                        onClick={() => handleDelete(char.id)}
                      >
                        Hapus
                      </button>
                    </div>
                  </div>
                  {char.appearance && (
                    <p className="mt-0.5 line-clamp-2 text-[11px] text-slate-400">{char.appearance}</p>
                  )}
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {char.costumes.map((cos) => (
                      <span key={cos.id} className="badge bg-ink-800 text-slate-300">
                        {cos.name}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))
          )}
        </section>
      </div>
    </div>
  )
}
