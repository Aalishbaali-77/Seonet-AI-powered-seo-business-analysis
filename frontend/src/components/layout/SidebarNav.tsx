"use client";

import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import { Box, Collapse, List, ListItemButton, ListItemIcon, ListItemText, Paper, Popper, Tooltip, Typography } from "@mui/material";
import { usePathname, useRouter } from "next/navigation";
import { useState, type MouseEvent } from "react";

import type { NavItem } from "@/config/navigation";
import { navIcon } from "@/config/navIcons";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { sidebarToggled } from "@/store/slices/uiSlice";

function isEnabled(item: NavItem, flags: Record<string, boolean>, modules: string[], access: boolean) {
  if (!access && !item.bypassLock) {
    return false;
  }
  if (item.flag && !flags[item.flag]) {
    return false;
  }
  if (item.module && !modules.includes(item.module)) {
    return false;
  }
  return true;
}

function NavGroup({ item, modules, collapsed, access }: { item: NavItem; modules: string[]; collapsed: boolean; access: boolean }) {
  const pathname = usePathname();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const flags = useAppSelector((state) => state.ui.featureFlags);
  const enabled = isEnabled(item, flags, modules, access);
  const children = (item.children ?? []).filter((child) => isEnabled(child, flags, modules, access));
  const [open, setOpen] = useState(pathname.startsWith(item.href));
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const Icon = navIcon(item.id);
  const selected = pathname === item.href || pathname.startsWith(`${item.href}/`);

  if (!enabled) {
    return null;
  }

  const go = (href: string) => {
    router.push(href);
    dispatch(sidebarToggled(false));
    setAnchor(null);
  };

  const onParentClick = (event: MouseEvent<HTMLElement>) => {
    if (collapsed && children.length) {
      setAnchor(anchor ? null : event.currentTarget);
      return;
    }
    if (children.length) {
      setOpen((value) => !value);
      return;
    }
    go(item.href);
  };

  const button = (
    <ListItemButton
      selected={selected}
      onClick={onParentClick}
      sx={{
        mx: collapsed ? 0.75 : 1,
        borderRadius: 1.5,
        mb: 0.25,
        justifyContent: collapsed ? "center" : "flex-start",
        px: collapsed ? 1 : 2,
        minHeight: 44,
      }}
    >
      <ListItemIcon sx={{ minWidth: collapsed ? 0 : 40, color: selected ? "primary.main" : "text.secondary", justifyContent: "center" }}>
        <Icon fontSize="small" />
      </ListItemIcon>
      {collapsed ? null : (
        <>
          <ListItemText primary={item.label} />
          {children.length ? open ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" /> : null}
        </>
      )}
    </ListItemButton>
  );

  return (
    <>
      {collapsed ? (
        <Tooltip title={item.label} placement="right">
          {button}
        </Tooltip>
      ) : (
        button
      )}
      {collapsed && children.length ? (
        <Popper open={Boolean(anchor)} anchorEl={anchor} placement="right-start" sx={{ zIndex: 1300 }}>
          <Paper elevation={8} sx={{ ml: 1, minWidth: 220, py: 1 }} onMouseLeave={() => setAnchor(null)}>
            <List disablePadding>
              <ListItemButton selected={pathname === item.href} onClick={() => go(item.href)}>
                <ListItemText primary={item.label} />
              </ListItemButton>
              {children.map((child) => {
                const ChildIcon = navIcon(child.id);
                return (
                  <ListItemButton
                    key={child.id}
                    selected={pathname === child.href || (child.href !== "/app/settings" && pathname.startsWith(`${child.href}/`))}
                    onClick={() => go(child.href)}
                  >
                    <ListItemIcon sx={{ minWidth: 36, color: "text.secondary" }}>
                      <ChildIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={child.label} />
                  </ListItemButton>
                );
              })}
            </List>
          </Paper>
        </Popper>
      ) : null}
      {!collapsed && children.length ? (
        <Collapse in={open} timeout="auto" unmountOnExit>
          <List disablePadding>
            {children.map((child) => {
              const ChildIcon = navIcon(child.id);
              const childSelected = pathname === child.href || (child.href !== "/app/settings" && pathname.startsWith(`${child.href}/`));
              return (
                <ListItemButton
                  key={child.id}
                  sx={{ pl: 4, mx: 1, borderRadius: 1.5, mb: 0.25, minHeight: 40 }}
                  selected={childSelected}
                  onClick={() => go(child.href)}
                >
                  <ListItemIcon sx={{ minWidth: 36, color: childSelected ? "primary.main" : "text.secondary" }}>
                    <ChildIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText primary={child.label} />
                </ListItemButton>
              );
            })}
          </List>
        </Collapse>
      ) : null}
    </>
  );
}

export function SidebarNav({
  items,
  label,
  enforceModules = true,
  collapsed = false,
}: {
  items: NavItem[];
  label: string;
  enforceModules?: boolean;
  collapsed?: boolean;
}) {
  const modules = useAppSelector((state) => (enforceModules ? state.auth.user?.modules ?? [] : []));
  const access = useAppSelector((state) => (enforceModules ? state.auth.user?.subscription?.access !== false : true));
  return (
    <Box sx={{ py: 1.5, flex: 1, overflowY: "auto" }}>
      {collapsed ? null : (
        <Typography variant="subtitle2" color="text.secondary" sx={{ px: 2, mb: 1 }}>
          {label}
        </Typography>
      )}
      <List>
        {items.map((item) => (
          <NavGroup key={item.id} item={item} modules={enforceModules ? modules : []} collapsed={collapsed} access={enforceModules ? access : true} />
        ))}
      </List>
    </Box>
  );
}
