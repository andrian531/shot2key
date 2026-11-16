import { Outlet } from 'react-router-dom'
import SystemStatusBar from './components/SystemStatusBar'
import { AppProvider } from './state/AppContext'

/**
 * Shell for every page: shared state, the status/navigation header, and the
 * routed view below it.
 */
export default function AppLayout() {
  return (
    <AppProvider>
      <div className="min-h-full pb-10">
        <SystemStatusBar />
        <Outlet />
      </div>
    </AppProvider>
  )
}
