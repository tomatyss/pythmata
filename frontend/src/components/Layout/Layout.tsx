import React, { useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import {
  AppBar,
  Avatar,
  Box,
  CssBaseline,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Toolbar,
  Typography,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  List as ListIcon,
  Add as AddIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material';
import { useAuthContext } from '@/context/AuthContext';

const drawerWidth = 240;

const menuItems = [
  { text: 'Dashboard', icon: React.createElement(DashboardIcon), path: '/' },
  {
    text: 'Processes',
    icon: React.createElement(ListIcon),
    path: '/processes',
  },
  {
    text: 'New Process',
    icon: React.createElement(AddIcon),
    path: '/processes/new',
  },
];

const Layout = () => {
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const { user, logout } = useAuthContext();

  const open = Boolean(anchorEl);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleMenuClose();
    logout();
  };

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          Pythmata
        </Typography>
      </Toolbar>
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton onClick={() => navigate(item.path)}>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', flex: 1 }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Workflow Engine
          </Typography>
          {user && (
            <>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'pointer',
                }}
                onClick={handleMenuOpen}
                aria-controls={open ? 'user-menu' : undefined}
                aria-haspopup="true"
                aria-expanded={open ? 'true' : undefined}
              >
                <Typography variant="body1" sx={{ mr: 1 }}>
                  {user?.full_name || user?.email || 'User'}
                </Typography>
                <Avatar sx={{ width: 32, height: 32 }}>
                  {user?.full_name?.[0]?.toUpperCase() ||
                    user?.email?.[0]?.toUpperCase() ||
                    'U'}
                </Avatar>
              </Box>
              <Menu
                id="user-menu"
                anchorEl={anchorEl}
                open={open}
                onClose={handleMenuClose}
                MenuListProps={{
                  'aria-labelledby': 'user-menu-button',
                }}
                anchorOrigin={{
                  vertical: 'bottom',
                  horizontal: 'right',
                }}
                transformOrigin={{
                  vertical: 'top',
                  horizontal: 'right',
                }}
              >
                <MenuItem onClick={handleLogout}>
                  <LogoutIcon fontSize="small" sx={{ mr: 1 }} />
                  Sign out
                </MenuItem>
              </Menu>
            </>
          )}
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        {/* Mobile drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>
        {/* Desktop drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: '100%',
          maxWidth: { sm: `calc(100% - ${drawerWidth}px)` },
        }}
      >
        <Toolbar /> {/* Spacer for AppBar */}
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;
