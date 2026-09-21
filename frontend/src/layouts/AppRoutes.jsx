import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import LoadingScreen from '../components/LoadingScreen.jsx'
import { useAuth } from '../services/auth.js'
import Login from '../pages/Login.jsx'
import Dashboard from '../pages/Dashboard.jsx'
import Connections from '../pages/Connections.jsx'
import AvailableConnections from '../pages/AvailableConnections.jsx'
import SnowflakeConnection from '../pages/SnowflakeConnection.jsx'
import MetadataExplorer from '../pages/MetadataExplorer.jsx'
import PipelineRuns from '../pages/PipelineRuns.jsx'
import ConnectionDetails from '../pages/ConnectionDetails.jsx'
import CreatePipeline from '../pages/CreatePipeline.jsx'


function ProtectedRoute() {
  const { isLoading, isAuthenticated } = useAuth()

  if (isLoading) 
    return <LoadingScreen />

  if (!isAuthenticated)
     return <Navigate to="/login" replace />

  return <Outlet />
}


function AppRoutes({ layout: Layout }) {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="connections" element={<Connections />} />
          <Route path="connections/available" element={<AvailableConnections />} />
          <Route path="connections/snowflake" element={<SnowflakeConnection />} />
          <Route path="connections/:connectionId" element={<ConnectionDetails />} />
          <Route path="connections/:connectionId/pipelines/new" element={<CreatePipeline />} />
          <Route path="metadata" element={<MetadataExplorer />} />
          <Route path="pipeline-runs" element={<PipelineRuns />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default AppRoutes
