"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/feedback/EmptyState";
import { useAppSelector } from "@/store/hooks";

export function ModuleGate({ module, children }: { module: string; children: ReactNode }) {
  const router = useRouter();
  const modules = useAppSelector((state) => state.auth.user?.modules ?? []);
  if (!modules.includes(module)) {
    return (
      <EmptyState
        title="Not on this package"
        description={`${module} is not assigned to this workspace. Choose a package that includes it, or ask SI Global to enable the module.`}
        actionLabel="Open subscription"
        onAction={() => router.push("/app/billing")}
      />
    );
  }
  return children;
}
