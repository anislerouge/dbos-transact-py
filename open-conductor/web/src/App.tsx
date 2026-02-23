import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import AppList from './pages/AppList'
import WorkflowList from './pages/WorkflowList'
import WorkflowDetail from './pages/WorkflowDetail'
import QueueView from './pages/QueueView'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/apps" element={<AppList />} />
        <Route path="/apps/:appName/workflows" element={<WorkflowList />} />
        <Route path="/apps/:appName/workflows/:workflowId" element={<WorkflowDetail />} />
        <Route path="/apps/:appName/queues" element={<QueueView />} />
      </Routes>
    </Layout>
  )
}
