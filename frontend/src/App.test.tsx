import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from './App';

// Mock page components
jest.mock('./pages/Dashboard');
jest.mock('./pages/ProcessList', () => () => <div>Process List Mock</div>);
jest.mock('./pages/ProcessDesigner', () => () => (
  <div>Process Designer Mock</div>
));
jest.mock('./pages/ProcessInstance', () => () => (
  <div>Process Instance Mock</div>
));
jest.mock('./pages/NotFound', () => () => <div>Not Found Mock</div>);

// Mock MUI components
jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  AppBar: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="app-bar">{children}</div>
  ),
  Drawer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="drawer">{children}</div>
  ),
  IconButton: ({ children }: { children: React.ReactNode }) => (
    <button>{children}</button>
  ),
  Toolbar: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  Typography: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  Box: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  List: ({ children }: { children: React.ReactNode }) => <ul>{children}</ul>,
  ListItem: ({ children }: { children: React.ReactNode }) => (
    <li>{children}</li>
  ),
  ListItemButton: ({
    children,
    onClick,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
  }) => <button onClick={onClick}>{children}</button>,
  ListItemIcon: ({ children }: { children: React.ReactNode }) => (
    <span>{children}</span>
  ),
  ListItemText: ({ primary }: { primary: string }) => <span>{primary}</span>,
  CssBaseline: () => null,
}));

// Mock MUI icons
jest.mock('@mui/icons-material', () => ({
  Menu: () => 'MenuIcon',
  Dashboard: () => 'DashboardIcon',
  List: () => 'ListIcon',
  Add: () => 'AddIcon',
}));

describe('App', () => {
  it('renders without crashing', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    expect(screen.getByTestId('app-bar')).toBeInTheDocument();
    // We expect to find two drawers (mobile and desktop)
    expect(screen.getAllByTestId('drawer')).toHaveLength(2);
  });
});
