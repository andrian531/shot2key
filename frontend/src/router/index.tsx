import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from '../App'
import LibraryView from '../views/LibraryView'
import ProjectView from '../views/ProjectView'
import CharactersView from '../views/CharactersView'
import SettingsView from '../views/SettingsView'

/**
 * Route table. Every page is a real URL, so F5 on /projects/:id reopens the
 * same project (the backend serves index.html for unknown paths).
 */
export default function AppRouter() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<LibraryView />} />
        <Route path="projects/:id" element={<ProjectView />} />
        <Route path="characters" element={<CharactersView />} />
        <Route path="settings" element={<SettingsView />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
