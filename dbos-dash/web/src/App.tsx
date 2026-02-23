import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import WorkflowList from './pages/WorkflowList'
import WorkflowDetail from './pages/WorkflowDetail'
import QueueView from './pages/QueueView'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/workflows" element={<WorkflowList />} />
        <Route path="/workflows/:workflowId" element={<WorkflowDetail />} />
        <Route path="/queues" element={<QueueView />} />
      </Routes>
    </Layout>
  )
}
