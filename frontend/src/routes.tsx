import { lazy, Suspense } from 'react';
import { RouteObject } from 'react-router-dom';
import { ROUTES } from '@/constants';
import Layout from '@/components/Layout';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import ProtectedRoute from '@/components/shared/ProtectedRoute';

// Lazy load components
const Login = lazy(() => import('@/pages/Login'));
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const ProcessList = lazy(() => import('@/pages/ProcessList'));
const ProcessDesigner = lazy(() => import('@/pages/ProcessDesigner'));
const ProcessInstance = lazy(() => import('@/pages/ProcessInstance'));
const ProcessInstanceList = lazy(() => import('@/pages/ProcessInstanceList'));
const ProcessDiagram = lazy(() => import('@/pages/ProcessDiagram'));
const NotFound = lazy(() => import('@/pages/NotFound'));

// Wrap lazy loaded components with Suspense
const withSuspense = (Component: React.ComponentType) => (
  <Suspense fallback={<LoadingSpinner fullHeight />}>
    <Component />
  </Suspense>
);

// Define routes configuration
const routes: RouteObject[] = [
  {
    path: ROUTES.LOGIN,
    element: withSuspense(Login),
  },
  {
    path: ROUTES.HOME,
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: withSuspense(Dashboard),
      },
      {
        path: ROUTES.DASHBOARD,
        element: withSuspense(Dashboard),
      },
      {
        path: ROUTES.PROCESSES,
        children: [
          {
            index: true,
            element: withSuspense(ProcessList),
          },
          {
            path: 'new',
            element: withSuspense(ProcessDesigner),
          },
          {
            path: ':id',
            children: [
              {
                index: true,
                element: withSuspense(ProcessDesigner),
              },
              {
                path: 'diagram',
                element: withSuspense(ProcessDiagram),
                id: 'process-diagram',
              },
              {
                path: 'instances',
                children: [
                  {
                    index: true,
                    element: withSuspense(ProcessInstanceList),
                  },
                  {
                    path: ':instanceId',
                    element: withSuspense(ProcessInstance),
                  },
                ],
              },
            ],
          },
        ],
      },
      {
        path: '*',
        element: withSuspense(NotFound),
      },
    ],
  },
];

export default routes;
