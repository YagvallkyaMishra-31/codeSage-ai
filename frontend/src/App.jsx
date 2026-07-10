import { Routes, Route } from 'react-router-dom'
import Layout from './layouts/Layout'
import Dashboard from './pages/Dashboard'
import RepositoryIndexing from './pages/RepositoryIndexing'
import DebugAssistant from './pages/DebugAssistant'
import RootCauseAnalysis from './pages/RootCauseAnalysis'
import ActivityHistory from './pages/ActivityHistory'
import RepoDetail from './pages/RepoDetail'
import SettingsPage from './pages/Settings'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/repositories" element={<RepositoryIndexing />} />
        <Route path="/debug" element={<DebugAssistant />} />
        <Route path="/analysis" element={<RootCauseAnalysis />} />
        <Route path="/activity" element={<ActivityHistory />} />
        <Route path="/repo/:id" element={<RepoDetail />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}

export default App
