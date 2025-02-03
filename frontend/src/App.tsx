import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';

import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import ProcessList from '@/pages/ProcessList';
import ProcessDesigner from '@/pages/ProcessDesigner';
import ProcessInstance from '@/pages/ProcessInstance';
import NotFound from '@/pages/NotFound';

const App = () => {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Routes>
        <Route path="/" element={<Layout />}>
          {/* Dashboard */}
          <Route index element={<Dashboard />} />

          {/* Process Management */}
          <Route path="processes">
            <Route index element={<ProcessList />} />
            <Route path="new" element={<ProcessDesigner />} />
            <Route path=":id">
              <Route index element={<ProcessDesigner />} />
              <Route
                path="instances/:instanceId"
                element={<ProcessInstance />}
              />
            </Route>
          </Route>

          {/* 404 Page */}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Box>
  );
};

export default App;
