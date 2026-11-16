import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api/client'
import type { Character, SystemStatus } from '../types'

interface AppState {
  status: SystemStatus | null
  characters: Character[]
  error: string | null
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
    () => ({ status, characters, error, setError, refreshStatus, refreshCharacters }),
    [status, characters, error, refreshStatus, refreshCharacters],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp(): AppState {
  const context = useContext(AppContext)
  if (!context) throw new Error('useApp must be used inside <AppProvider>')
  return context
}
