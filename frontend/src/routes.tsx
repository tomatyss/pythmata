import { lazy, Suspense } from 'react';
import { RouteObject } from 'react-router-dom';
import { ROUTES } from '@/constants';
import Layout from '@/components/Layout';
import LoadingSpinner from '@/components/shared/LoadingSpinner';

// Lazy load components
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const ProcessList = lazy(() => import('@/pages/ProcessList'));
const ProcessDesigner = lazy(() => import('@/pages/ProcessDesigner'));
const ProcessInstance = lazy(() => import('@/pages/ProcessInstance'));
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
    path: ROUTES.HOME,
    element: <Layout />,
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
                path: 'instances/:instanceId',
                element: withSuspense(ProcessInstance),
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
