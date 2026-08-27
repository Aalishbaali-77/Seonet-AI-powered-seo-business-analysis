"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { Box, Breadcrumbs, Link as MuiLink, Toolbar } from "@mui/material";
import NextLink from "next/link";
import { usePathname } from "next/navigation";

import { AppHeader } from "@/components/layout/AppHeader";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { CommandPalette } from "@/components/navigation/CommandPalette";
import type { NavItem } from "@/config/navigation";
import { useAppSelector } from "@/store/hooks";
import { layout } from "@/theme/spacing";

export function WorkspaceShell({
  children,
  items,
  navLabel,
  brandTitle,
  brandSubtitle,
  headerTitle,
  showTenantSwitcher,
  enforceModules,
  consoleHref,
  consoleLabel,
}: {
  children: ReactNode;
  items: NavItem[];
  navLabel: string;
  brandTitle: string;
  brandSubtitle: string;
  headerTitle: string;
  showTenantSwitcher: boolean;
  enforceModules: boolean;
  consoleHref?: string;
  consoleLabel?: string;
}) {
  const pathname = usePathname();
  const crumbs = pathname.split("/").filter(Boolean);
  const tenantId = useAppSelector((state) => state.tenant.currentId);
  const collapsed = useAppSelector((state) => state.ui.sidebarCollapsed);
  const sidebarWidth = collapsed ? layout.sidebarCollapsedWidth : layout.sidebarWidth;

  useEffect(() => {
    if (tenantId) {
      window.localStorage.setItem("seonet.tenant", tenantId);
    }
  }, [tenantId]);

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default", overflowX: "hidden" }}>
      <AppSidebar
        items={items}
        navLabel={navLabel}
        brandTitle={brandTitle}
        brandSubtitle={brandSubtitle}
        enforceModules={enforceModules}
      />
      <AppHeader
        title={headerTitle}
        showTenantSwitcher={showTenantSwitcher}
        consoleHref={consoleHref}
        consoleLabel={consoleLabel}
        sidebarWidth={sidebarWidth}
      />
      <CommandPalette items={items} />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          minWidth: 0,
          width: "auto",
          px: { xs: 2, sm: 2.5, md: 3 },
          py: { xs: 2, md: 3 },
          overflowX: "hidden",
        }}
      >
        <Toolbar className="no-print" />
        <Breadcrumbs className="no-print" sx={{ mb: 2, display: { xs: "none", sm: "flex" } }} aria-label="Breadcrumb">
          {crumbs.map((crumb, index) => {
            const href = `/${crumbs.slice(0, index + 1).join("/")}`;
            const label = crumb.replace(/-/g, " ");
            return (
              <MuiLink key={href} component={NextLink} href={href} underline="hover" color="inherit" sx={{ textTransform: "capitalize" }}>
                {label}
              </MuiLink>
            );
          })}
        </Breadcrumbs>
        <Box sx={{ maxWidth: layout.contentMaxWidth, mx: "auto" }}>{children}</Box>
      </Box>
    </Box>
  );
}
