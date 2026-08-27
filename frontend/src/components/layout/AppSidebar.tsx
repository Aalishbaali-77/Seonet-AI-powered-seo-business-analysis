"use client";

import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import { Box, Drawer, IconButton, Tooltip } from "@mui/material";
import { useEffect, useRef } from "react";

import { BrandMark } from "@/components/branding/BrandMark";
import { SidebarNav } from "@/components/layout/SidebarNav";
import type { NavItem } from "@/config/navigation";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { sidebarCollapsedToggled, sidebarToggled } from "@/store/slices/uiSlice";
import { layout } from "@/theme/spacing";

function Brand({ subtitle, collapsed }: { subtitle: string; collapsed: boolean }) {
  return (
    <Box sx={{ px: collapsed ? 1 : 2.25, py: collapsed ? 1.5 : 2, display: "flex", justifyContent: collapsed ? "center" : "flex-start", borderBottom: 1, borderColor: "divider" }}>
      <BrandMark variant={collapsed ? "collapsed" : "sidebar"} subtitle={collapsed ? undefined : subtitle} />
    </Box>
  );
}

export function AppSidebar({
  items,
  navLabel,
  brandSubtitle,
  enforceModules,
}: {
  items: NavItem[];
  navLabel: string;
  brandTitle?: string;
  brandSubtitle: string;
  enforceModules: boolean;
}) {
  const mobileOpen = useAppSelector((state) => state.ui.sidebarOpen);
  const collapsed = useAppSelector((state) => state.ui.sidebarCollapsed);
  const dispatch = useAppDispatch();
  const desktopWidth = collapsed ? layout.sidebarCollapsedWidth : layout.sidebarWidth;

  const skipPersist = useRef(true);

  useEffect(() => {
    const stored = window.localStorage.getItem("sipulse.sidebarCollapsed");
    if (stored === "1") {
      dispatch(sidebarCollapsedToggled(true));
    }
  }, [dispatch]);

  useEffect(() => {
    if (skipPersist.current) {
      skipPersist.current = false;
      return;
    }
    window.localStorage.setItem("sipulse.sidebarCollapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  const contents = (rail: boolean) => (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Brand subtitle={brandSubtitle} collapsed={rail} />
      <SidebarNav items={items} label={navLabel} enforceModules={enforceModules} collapsed={rail} />
      <Box sx={{ borderTop: 1, borderColor: "divider", p: 1, display: { xs: "none", md: "flex" }, justifyContent: rail ? "center" : "flex-end" }}>
        <Tooltip title={rail ? "Expand sidebar" : "Collapse sidebar"}>
          <IconButton aria-label={rail ? "Expand sidebar" : "Collapse sidebar"} onClick={() => dispatch(sidebarCollapsedToggled())} size="small">
            {rail ? <ChevronRightIcon /> : <ChevronLeftIcon />}
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );

  return (
    <>
      <Drawer
        className="no-print"
        variant="temporary"
        open={mobileOpen}
        onClose={() => dispatch(sidebarToggled(false))}
        ModalProps={{ keepMounted: true }}
        sx={{ display: { xs: "block", md: "none" }, "& .MuiDrawer-paper": { width: layout.sidebarWidth } }}
      >
        {contents(false)}
      </Drawer>
      <Drawer
        className="no-print"
        variant="permanent"
        open
        sx={{
          display: { xs: "none", md: "block" },
          width: desktopWidth,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: desktopWidth,
            boxSizing: "border-box",
            borderRight: 1,
            borderColor: "divider",
            overflowX: "hidden",
            transition: (theme) => theme.transitions.create("width", { duration: theme.transitions.duration.shortest }),
          },
        }}
      >
        {contents(collapsed)}
      </Drawer>
    </>
  );
}
