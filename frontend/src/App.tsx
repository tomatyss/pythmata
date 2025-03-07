import { BrowserRouter } from 'react-router-dom';
import { Box } from '@mui/material';
import { AuthProvider } from '@/context/AuthContext';
import { useRoutes } from 'react-router-dom';
import routes from './routes';

const AppRoutes = () => {
  return useRoutes(routes);
};

const App = () => {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </Box>
  );
};

export default App;
