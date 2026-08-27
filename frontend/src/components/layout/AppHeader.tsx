"use client";

import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import HelpOutlineIcon from "@mui/icons-material/HelpOutlineOutlined";
import LogoutIcon from "@mui/icons-material/Logout";
import MenuIcon from "@mui/icons-material/Menu";
import NotificationsNoneIcon from "@mui/icons-material/NotificationsNone";
import SearchIcon from "@mui/icons-material/Search";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import SpaceDashboardIcon from "@mui/icons-material/SpaceDashboard";
import {
  AppBar,
  Avatar,
  Badge,
  Box,
  Button,
  Divider,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Menu,
  MenuItem,
  Popover,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { TenantSwitcher } from "@/components/navigation/TenantSwitcher";
import { notificationApi } from "@/services/platformApi";
import { layout } from "@/theme/spacing";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { logoutRequested } from "@/store/slices/authSlice";
import { notificationRead, notificationsRequested } from "@/store/slices/dashboardSlice";
import { commandToggled, sidebarCollapsedToggled, sidebarToggled } from "@/store/slices/uiSlice";

export function AppHeader({
  title,
  showTenantSwitcher,
  consoleHref,
  consoleLabel,
  sidebarWidth = layout.sidebarWidth,
}: {
  title: string;
  showTenantSwitcher: boolean;
  consoleHref?: string;
  consoleLabel?: string;
  sidebarWidth?: number;
}) {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const user = useAppSelector((state) => state.auth.user);
  const notifications = useAppSelector((state) => state.dashboard.notifications);
  const collapsed = useAppSelector((state) => state.ui.sidebarCollapsed);
  const tenantId = useAppSelector((state) => state.tenant.currentId);
  const unread = notifications.filter((item) => !item.read_at).length;
  const [accountEl, setAccountEl] = useState<HTMLElement | null>(null);
  const [noticeEl, setNoticeEl] = useState<HTMLElement | null>(null);
  const settingsHref = showTenantSwitcher ? "/app/settings" : "/platform/settings";

  useEffect(() => {
    dispatch(notificationsRequested());
  }, [dispatch, tenantId]);

  const openNotification = (item: (typeof notifications)[number]) => {
    if (!item.read_at) {
      const readAt = new Date().toISOString();
      dispatch(notificationRead({ id: item.id, read_at: readAt }));
      void notificationApi.markRead(item.id).catch(() => undefined);
    }
    setNoticeEl(null);
    if (item.link) {
      router.push(item.link);
    }
  };

  return (
    <AppBar
      className="no-print"
      position="fixed"
      color="inherit"
      elevation={0}
      sx={{
        borderBottom: 1,
        borderColor: "divider",
        ml: { md: `${sidebarWidth}px` },
        width: { md: `calc(100% - ${sidebarWidth}px)` },
        transition: (theme) => theme.transitions.create(["margin", "width"], { duration: theme.transitions.duration.shortest }),
      }}
    >
      <Toolbar sx={{ gap: 0.5, minHeight: { xs: 56, md: layout.headerHeight }, px: { xs: 1, sm: 2 } }}>
        <Tooltip title="Open navigation">
          <IconButton aria-label="Toggle navigation" onClick={() => dispatch(sidebarToggled(true))} sx={{ display: { md: "none" } }}>
            <MenuIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          <IconButton
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => dispatch(sidebarCollapsedToggled())}
            sx={{ display: { xs: "none", md: "inline-flex" } }}
          >
            <MenuIcon />
          </IconButton>
        </Tooltip>
        <Typography variant="h5" sx={{ display: { xs: "none", sm: "block" }, mr: 1, whiteSpace: "nowrap" }}>
          {title}
        </Typography>
        {showTenantSwitcher ? <TenantSwitcher /> : null}
        <Box sx={{ flexGrow: 1 }} />
        {consoleHref && consoleLabel ? (
          <Tooltip title={consoleLabel}>
            <IconButton aria-label={consoleLabel} onClick={() => router.push(consoleHref)}>
              {consoleHref.startsWith("/platform") ? <AdminPanelSettingsIcon /> : <SpaceDashboardIcon />}
            </IconButton>
          </Tooltip>
        ) : null}
        <Tooltip title="Search (Ctrl+K)">
          <IconButton aria-label="Search" onClick={() => dispatch(commandToggled(true))}>
            <SearchIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Notifications">
          <IconButton
            aria-label="Notifications"
            aria-haspopup="true"
            aria-expanded={Boolean(noticeEl)}
            onClick={(event) => {
              setAccountEl(null);
              setNoticeEl(event.currentTarget);
              dispatch(notificationsRequested());
            }}
          >
            <Badge badgeContent={unread} color="secondary" max={9}>
              <NotificationsNoneIcon />
            </Badge>
          </IconButton>
        </Tooltip>
        <Tooltip title="Help">
          <IconButton
            aria-label="Help"
            onClick={() => router.push("/docs")}
            sx={{ display: { xs: "none", sm: "inline-flex" } }}
          >
            <HelpOutlineIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Account">
          <IconButton
            aria-label="Account menu"
            aria-haspopup="true"
            onClick={(event) => {
              setNoticeEl(null);
              setAccountEl(event.currentTarget);
            }}
          >
            <Avatar sx={{ width: 32, height: 32 }}>
              {(user?.first_name || user?.email || "U").slice(0, 1).toUpperCase()}
            </Avatar>
          </IconButton>
        </Tooltip>
        <Popover
          anchorEl={noticeEl}
          open={Boolean(noticeEl)}
          onClose={() => setNoticeEl(null)}
          anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
          transformOrigin={{ vertical: "top", horizontal: "right" }}
          slotProps={{ paper: { sx: { width: 360, maxWidth: "calc(100vw - 24px)", maxHeight: 440, mt: 1 } } }}
        >
          <Box sx={{ px: 2, py: 1.5 }}>
            <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center" }}>
              <Typography variant="h5">Notifications</Typography>
              {unread ? (
                <Button
                  size="small"
                  onClick={() =>
                    void notificationApi.markAllRead().then(() => dispatch(notificationsRequested())).catch(() => undefined)
                  }
                >
                  Mark all read
                </Button>
              ) : null}
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {unread ? `${unread} unread` : "You're up to date"}
            </Typography>
          </Box>
          <Divider />
          {notifications.length ? (
            <List dense disablePadding>
              {notifications.map((item) => (
                <ListItemButton
                  key={item.id}
                  alignItems="flex-start"
                  selected={!item.read_at}
                  onClick={() => openNotification(item)}
                >
                  <ListItemText
                    primary={item.title}
                    secondary={
                      <>
                        {item.body || " "}
                        <Typography component="span" variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                          {item.created_at ? new Date(item.created_at).toLocaleString() : ""}
                        </Typography>
                      </>
                    }
                    slotProps={{
                      primary: { sx: { fontWeight: item.read_at ? 400 : 600 } },
                    }}
                  />
                </ListItemButton>
              ))}
            </List>
          ) : (
            <Typography color="text.secondary" sx={{ px: 2, py: 3 }}>
              No notifications yet.
            </Typography>
          )}
        </Popover>
        <Menu
          anchorEl={accountEl}
          open={Boolean(accountEl)}
          onClose={() => setAccountEl(null)}
          anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
          transformOrigin={{ vertical: "top", horizontal: "right" }}
        >
          <MenuItem disabled>{user?.email}</MenuItem>
          {consoleHref ? (
            <MenuItem
              onClick={() => {
                setAccountEl(null);
                router.push(consoleHref);
              }}
            >
              {consoleLabel}
            </MenuItem>
          ) : null}
          <MenuItem
            onClick={() => {
              setAccountEl(null);
              router.push(settingsHref);
            }}
          >
            <SettingsOutlinedIcon fontSize="small" sx={{ mr: 1 }} /> Settings
          </MenuItem>
          <MenuItem
            onClick={() => {
              setAccountEl(null);
              dispatch(logoutRequested());
            }}
          >
            <LogoutIcon fontSize="small" sx={{ mr: 1 }} /> Sign out
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
}
