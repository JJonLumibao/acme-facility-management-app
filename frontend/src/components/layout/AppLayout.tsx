import { useEffect, useState } from 'react';
import type { MouseEvent } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Switch from '@mui/material/Switch';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import ApartmentIcon from '@mui/icons-material/Apartment';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import AssignmentIcon from '@mui/icons-material/Assignment';
import BusinessIcon from '@mui/icons-material/Business';
import EngineeringIcon from '@mui/icons-material/Engineering';
import type { ReactElement } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useCatalog } from '../../context/CatalogContext';
import ResetDemoDialog from './ResetDemoDialog';
import AssistantPanel from '../assistant/AssistantPanel';
import { getEngineer, updateEngineer } from '../../services/engineerService';
import type { Role } from '../../types';
import { ROLE_LABELS } from '../../utils/format';
import '../../styles/layout.css';

const NAV_LINKS: Array<{ to: string; label: string; icon: ReactElement; roles: Role[] | null }> = [
  { to: '/', label: 'Dashboard', icon: <DashboardIcon />, roles: null },
  { to: '/incidents', label: 'Incidents', icon: <AssignmentIcon />, roles: null },
  { to: '/facilities', label: 'Facilities', icon: <BusinessIcon />, roles: ['facility_admin'] },
  { to: '/engineers', label: 'Engineers', icon: <EngineeringIcon />, roles: ['facility_admin'] },
];

/** Top navigation bar (role-aware links + account menu, drawer on mobile) wrapping every authenticated page. */
export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [isAvailable, setIsAvailable] = useState<boolean | null>(null);
  const [resetOpen, setResetOpen] = useState(false);
  const { catalog } = useCatalog();

  const isEngineer = user?.role === 'engineer';
  const links = NAV_LINKS.filter((link) => !link.roles || (user && link.roles.includes(user.role)));

  useEffect(() => {
    if (isEngineer && user) {
      getEngineer(user.id)
        .then((profile) => setIsAvailable(profile.is_available))
        .catch(() => setIsAvailable(null));
    }
  }, [isEngineer, user]);

  const handleMenuOpen = (event: MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);

  const handleLogout = () => {
    handleMenuClose();
    logout();
    navigate('/login');
  };

  const handleDemoReset = () => {
    setResetOpen(false);
    logout();
    navigate('/login', { state: { notice: 'Demo data restored. Sign in again.' } });
  };

  const toggleAvailability = async () => {
    if (!user || isAvailable === null) return;
    const next = !isAvailable;
    setIsAvailable(next);
    try {
      await updateEngineer(user.id, { is_available: next });
    } catch {
      setIsAvailable(!next);
    }
  };

  return (
    <div className="app-shell">
      <AppBar position="sticky" color="default" elevation={0} sx={{ borderBottom: '1px solid var(--color-border)', bgcolor: 'background.paper' }}>
        <Toolbar>
          {isMobile && (
            <IconButton edge="start" aria-label="Open navigation" onClick={() => setDrawerOpen(true)} sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
          )}
          <ApartmentIcon color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6" className="app-toolbar-title" noWrap>
            ACME Facilities
          </Typography>
          {!isMobile && (
            <Box className="app-nav-links" component="nav">
              {links.map((link) => (
                <Button
                  key={link.to}
                  component={NavLink}
                  to={link.to}
                  end={link.to === '/'}
                  color="inherit"
                  sx={{ '&.active': { fontWeight: 700, color: 'primary.main' } }}
                >
                  {link.label}
                </Button>
              ))}
            </Box>
          )}
          <IconButton onClick={handleMenuOpen} sx={{ ml: 1 }} aria-label="Account menu">
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 14 }}>
              {user?.full_name?.[0]?.toUpperCase() ?? '?'}
            </Avatar>
          </IconButton>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleMenuClose}>
            <Box sx={{ px: 2, py: 1 }}>
              <Typography variant="subtitle2">{user?.full_name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {user ? ROLE_LABELS[user.role] : ''} · {user?.email}
              </Typography>
            </Box>
            {isEngineer && isAvailable !== null && [
              <Divider key="divider" />,
              <MenuItem key="availability" onClick={toggleAvailability}>
                <ListItemText primary="Available for new tickets" />
                <Switch edge="end" size="small" checked={isAvailable} tabIndex={-1} />
              </MenuItem>,
            ]}
            {catalog?.demo_reset_enabled && [
              <Divider key="reset-divider" />,
              <MenuItem
                key="reset"
                onClick={() => {
                  handleMenuClose();
                  setResetOpen(true);
                }}
                sx={{ color: 'error.main' }}
              >
                Reset demo data…
              </MenuItem>,
            ]}
            <Divider />
            <MenuItem onClick={handleLogout}>Log out</MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
        <Box sx={{ width: 250 }} role="navigation" onClick={() => setDrawerOpen(false)}>
          <Toolbar>
            <ApartmentIcon color="primary" sx={{ mr: 1 }} />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              ACME Facilities
            </Typography>
          </Toolbar>
          <Divider />
          <List>
            {links.map((link) => (
              <ListItemButton
                key={link.to}
                component={NavLink}
                to={link.to}
                end={link.to === '/'}
                sx={{ '&.active': { color: 'primary.main', fontWeight: 700, bgcolor: 'action.selected' } }}
              >
                <ListItemIcon sx={{ color: 'inherit' }}>{link.icon}</ListItemIcon>
                <ListItemText primary={link.label} />
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>

      <main className="app-content">
        <Outlet />
      </main>

      <AssistantPanel />
      <ResetDemoDialog open={resetOpen} onClose={() => setResetOpen(false)} onReset={handleDemoReset} />
    </div>
  );
}
