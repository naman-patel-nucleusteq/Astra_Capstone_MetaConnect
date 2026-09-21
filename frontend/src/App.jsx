
import { BrowserRouter } from 'react-router-dom'
import AppLayout from './layouts/AppLayout.jsx'
import AppRoutes from './layouts/AppRoutes.jsx'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <AppRoutes layout={AppLayout} />
    </BrowserRouter>
  )
}

export default App
