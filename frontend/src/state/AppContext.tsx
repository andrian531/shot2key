import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api/client'
import { DEFAULT_LANG, TRANSLATIONS, readStoredLang, saveStoredLang } from '../i18n'
import type { UILang, UIStrings } from '../i18n'
import type { Character, SystemStatus } from '../types'

interface AppState {
  status: SystemStatus | null
  characters: Character[]
  error: string | null
  lang: UILang
  t: UIStrings
  setLang: (lang: UILang) => void
  setError: (message: string | null) => void
  refreshStatus: () => Promise<void>
  refreshCharacters: () => Promise<void>
}

const AppContext = createContext<AppState | null>(null)

/**
 * Shared state for the header (dependency pills) and the views that need the
 * character database. Loaded once per page load, refreshed on demand.
 */
export function AppProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [characters, setCharacters] = useState<Character[]>([])
  const [error, setError] = useState<string | null>(null)
  const [lang, setLangState] = useState<UILang>(() => readStoredLang() ?? DEFAULT_LANG)

  const setLang = useCallback((next: UILang) => {
    setLangState(next)
    saveStoredLang(next)
  }, [])

  const t = TRANSLATIONS[lang]

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  const refreshStatus = useCallback(async () => {
    try {
      setStatus(await api.status())
    } catch (err) {
      setError((err as Error).message)
    }
  }, [])

  const refreshCharacters = useCallback(async () => {
    try {
      setCharacters(await api.listCharacters())
    } catch (err) {
      setError((err as Error).message)
    }
  }, [])

  useEffect(() => {
    void refreshStatus()
    void refreshCharacters()
  }, [refreshStatus, refreshCharacters])

  const value = useMemo(
    () => ({ status, characters, error, lang, t, setLang, setError, refreshStatus, refreshCharacters }),
    [status, characters, error, lang, t, setLang, refreshStatus, refreshCharacters],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp(): AppState {
  const context = useContext(AppContext)
  if (!context) throw new Error('useApp must be used inside <AppProvider>')
  return context
}
