import { Routes, Route, BrowserRouter } from 'react-router-dom';
import { Box } from '@mui/material';
import { AuthProvider } from '@/context/AuthContext';

import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import ProcessList from '@/pages/ProcessList';
import ProcessDesigner from '@/pages/ProcessDesigner';
import ProcessInstance from '@/pages/ProcessInstance';
import ProcessInstanceList from '@/pages/ProcessInstanceList';
import ProcessDiagram from '@/pages/ProcessDiagram';
import NotFound from '@/pages/NotFound';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import ProtectedRoute from '@/components/shared/ProtectedRoute';

const App = () => {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              {/* Dashboard */}
              <Route index element={<Dashboard />} />

              {/* Process Management */}
              <Route path="processes">
                <Route index element={<ProcessList />} />
                <Route path="new" element={<ProcessDesigner />} />
                <Route path=":id">
                  <Route index element={<ProcessDesigner />} />
                  <Route path="diagram" element={<ProcessDiagram />} />
                  <Route path="instances">
                    <Route index element={<ProcessInstanceList />} />
                    <Route path=":instanceId" element={<ProcessInstance />} />
                  </Route>
                </Route>
              </Route>

              {/* 404 Page */}
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </Box>
  );
};

export default App;
