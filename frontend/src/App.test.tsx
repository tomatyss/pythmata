import * as React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from './App';

// Mock Layout component
vi.mock('./components/Layout', () => ({
  default: () => (
    <>
      <div data-testid="app-bar">App Bar</div>
      <div data-testid="drawer">Drawer Content</div>
      <div data-testid="drawer">Drawer Content</div>
      <div data-testid="layout-content">Layout Content</div>
    </>
  ),
}));

// Mock page components
vi.mock('./pages/Dashboard');
vi.mock('./pages/ProcessList', () => ({
  default: () => <div>Process List Mock</div>,
}));

vi.mock('./pages/ProcessDesigner', () => ({
  default: () => <div>Process Designer Mock</div>,
}));

vi.mock('./pages/ProcessInstance', () => ({
  default: () => <div>Process Instance Mock</div>,
}));

vi.mock('./pages/NotFound', () => ({
  default: () => <div>Not Found Mock</div>,
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: '1', name: 'Test User', email: 'test@example.com' },
    loading: false,
    error: null,
    isAuthenticated: true,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

// Mock MUI components
vi.mock('@mui/material', () => {
  const actual = vi.importActual('@mui/material');
  return {
    ...actual,
    AppBar: function AppBar({ children }: { children: React.ReactNode }) {
      return React.createElement('div', { 'data-testid': 'app-bar' }, children);
    },
    Drawer: function Drawer({ children }: { children: React.ReactNode }) {
      return React.createElement('div', { 'data-testid': 'drawer' }, children);
    },
    IconButton: function IconButton({
      children,
    }: {
      children: React.ReactNode;
    }) {
      return React.createElement('button', null, children);
    },
    Toolbar: function Toolbar({ children }: { children: React.ReactNode }) {
      return React.createElement('div', null, children);
    },
    Typography: function Typography({
      children,
    }: {
      children: React.ReactNode;
    }) {
      return React.createElement('div', null, children);
    },
    Box: function Box({ children }: { children: React.ReactNode }) {
      return React.createElement('div', null, children);
    },
    List: function List({ children }: { children: React.ReactNode }) {
      return React.createElement('ul', null, children);
    },
    ListItem: function ListItem({ children }: { children: React.ReactNode }) {
      return React.createElement('li', null, children);
    },
    ListItemButton: function ListItemButton({
      children,
      onClick,
    }: {
      children: React.ReactNode;
      onClick?: () => void;
    }) {
      return React.createElement('button', { onClick }, children);
    },
    ListItemIcon: function ListItemIcon({
      children,
    }: {
      children: React.ReactNode;
    }) {
      return React.createElement('span', null, children);
    },
    ListItemText: function ListItemText({ primary }: { primary: string }) {
      return React.createElement('span', null, primary);
    },
    CssBaseline: function CssBaseline() {
      return null;
    },
    CircularProgress: function CircularProgress() {
      return React.createElement('div', { 'data-testid': 'circular-progress' });
    },
  };
});

// Mock MUI icons
vi.mock('@mui/icons-material', () => ({
  Menu: () => 'MenuIcon',
  Dashboard: () => 'DashboardIcon',
  List: () => 'ListIcon',
  Add: () => 'AddIcon',
}));

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(screen.getByTestId('app-bar')).toBeInTheDocument();
    // We expect to find two drawers (mobile and desktop)
    expect(screen.getAllByTestId('drawer')).toHaveLength(2);
  });
});
