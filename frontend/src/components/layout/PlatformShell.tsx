"use client";

import type { ReactNode } from "react";

import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
import { platformNavigation } from "@/config/navigation";
import { useAppSelector } from "@/store/hooks";

export function PlatformShell({ children }: { children: ReactNode }) {
  const hasTenant = (useAppSelector((state) => state.auth.user?.tenants.length) ?? 0) > 0;
  const owner = useAppSelector((state) => state.ui.branding.legal_name);
  return (
    <WorkspaceShell
      items={platformNavigation}
      navLabel="Control plane"
      brandTitle=""
      brandSubtitle={`${owner} control plane`}
      headerTitle="Platform"
      showTenantSwitcher={false}
      enforceModules={false}
      consoleHref={hasTenant ? "/app/dashboard" : undefined}
      consoleLabel={hasTenant ? "Tenant workspace" : undefined}
    >
      {children}
    </WorkspaceShell>
  );
}
