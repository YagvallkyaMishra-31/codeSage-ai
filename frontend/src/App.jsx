import { Routes, Route } from 'react-router-dom'
import Layout from './layouts/Layout'
import Dashboard from './pages/Dashboard'
import RepositoryIndexing from './pages/RepositoryIndexing'
import DebugAssistant from './pages/DebugAssistant'
import RootCauseAnalysis from './pages/RootCauseAnalysis'
import ActivityHistory from './pages/ActivityHistory'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/repositories" element={<RepositoryIndexing />} />
        <Route path="/debug" element={<DebugAssistant />} />
        <Route path="/analysis" element={<RootCauseAnalysis />} />
        <Route path="/activity" element={<ActivityHistory />} />
        <Route path="/settings" element={<div className="p-10"><h1 className="text-2xl font-semibold" style={{color:'var(--color-text-primary)'}}>Settings</h1><p className="mt-2" style={{color:'var(--color-text-secondary)'}}>Coming soon.</p></div>} />
      </Routes>
    </Layout>
  )
}

export default App
