"use client";

import { AppShell } from "@/components/layout/AppShell";
import { AuthGate } from "@/features/auth/AuthGate";

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <AppShell>{children}</AppShell>
    </AuthGate>
  );
}
