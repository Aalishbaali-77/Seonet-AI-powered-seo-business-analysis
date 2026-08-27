"use client";

import { AuthGate } from "@/features/auth/AuthGate";
import { PlatformShell } from "@/components/layout/PlatformShell";

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate platformOnly>
      <PlatformShell>{children}</PlatformShell>
    </AuthGate>
  );
}
