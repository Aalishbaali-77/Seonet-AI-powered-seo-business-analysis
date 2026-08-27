"use client";

import type { ReactNode } from "react";

import { PageTracker } from "@/components/layout/PageTracker";
import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
import { navigation } from "@/config/navigation";
import { AuditProgressHost } from "@/features/websites/AuditProgressHost";
import { AuditSessionProvider } from "@/features/websites/auditSession";
import { useAppSelector } from "@/store/hooks";

export function AppShell({ children }: { children: ReactNode }) {
  const user = useAppSelector((state) => state.auth.user);
  return (
    <AuditSessionProvider>
      <WorkspaceShell
        items={navigation}
        navLabel="Workspace"
        brandTitle=""
        brandSubtitle="Tenant workspace"
        headerTitle="Workspace"
        showTenantSwitcher
        enforceModules
        consoleHref={user?.is_platform_admin ? "/platform" : undefined}
        consoleLabel={user?.is_platform_admin ? "Platform console" : undefined}
      >
        {children}
      </WorkspaceShell>
      <PageTracker />
      <AuditProgressHost />
    </AuditSessionProvider>
  );
}
