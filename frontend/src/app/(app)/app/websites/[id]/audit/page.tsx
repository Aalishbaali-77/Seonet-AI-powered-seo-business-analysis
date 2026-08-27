"use client";

import { Suspense } from "react";

import { LoadingState } from "@/components/feedback/LoadingState";
import { WebsiteAuditProgressPage } from "@/features/websites/WebsiteAuditProgressPage";

export default function Page() {
  return (
    <Suspense fallback={<LoadingState />}>
      <WebsiteAuditProgressPage />
    </Suspense>
  );
}
