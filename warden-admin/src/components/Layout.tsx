import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  Typography, Divider, Toolbar,
} from '@mui/material'
import CameraAltIcon from '@mui/icons-material/CameraAlt'
import DashboardIcon from '@mui/icons-material/Dashboard'
import LogoutIcon from '@mui/icons-material/Logout'
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid'
import SettingsIcon from '@mui/icons-material/Settings'
import PeopleIcon from '@mui/icons-material/People'
import { useAuth } from '@/hooks/useAuth'

const DRAWER_WIDTH = 220

const nav = [
  { to: '/', label: 'Dashboard', icon: <DashboardIcon fontSize="small" />, end: true },
  { to: '/cameras', label: 'Cameras', icon: <CameraAltIcon fontSize="small" /> },
  { to: '/devices', label: 'Devices', icon: <PhoneAndroidIcon fontSize="small" /> },
  { to: '/users', label: 'Users', icon: <PeopleIcon fontSize="small" /> },
  { to: '/settings', label: 'Settings', icon: <SettingsIcon fontSize="small" /> },
]

export function Layout() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            bgcolor: 'background.paper',
            borderRight: '1px solid rgba(255,255,255,0.08)',
          },
        }}
      >
        <Toolbar sx={{ px: 2, minHeight: '64px !important', gap: 1.5 }}>
          <Box component="img" src="/logo.svg" alt="Warden" sx={{ height: 32 }} />
          <Typography variant="subtitle2" color="text.secondary" sx={{ letterSpacing: 0.5 }}>
            Admin
          </Typography>
        </Toolbar>
        <Divider />

        <List sx={{ flex: 1, px: 1, py: 1 }}>
          {nav.map(({ to, label, icon, end }) => (
            <NavLink key={to} to={to} end={end} style={{ textDecoration: 'none' }}>
              {({ isActive }) => (
                <ListItemButton
                  selected={isActive}
                  sx={{ borderRadius: 1, mb: 0.5 }}
                >
                  <ListItemIcon sx={{ minWidth: 36, color: isActive ? 'primary.main' : 'text.secondary' }}>
                    {icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={label}
                    primaryTypographyProps={{ fontSize: 14, color: isActive ? 'primary.main' : 'text.secondary' }}
                  />
                </ListItemButton>
              )}
            </NavLink>
          ))}
        </List>

        <Divider />
        <List sx={{ px: 1, py: 1 }}>
          <ListItemButton onClick={handleLogout} sx={{ borderRadius: 1 }}>
            <ListItemIcon sx={{ minWidth: 36, color: 'text.secondary' }}>
              <LogoutIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary="Sign out" primaryTypographyProps={{ fontSize: 14, color: 'text.secondary' }} />
          </ListItemButton>
        </List>
      </Drawer>

      <Box component="main" sx={{ flex: 1, overflow: 'auto' }}>
        <Outlet />
      </Box>
    </Box>
  )
}
