"use client";

import type { ReactNode } from "react";

import { ModuleGate } from "@/components/common/ModuleGate";

export default function Layout({ children }: { children: ReactNode }) {
  return <ModuleGate module="markets">{children}</ModuleGate>;
}
