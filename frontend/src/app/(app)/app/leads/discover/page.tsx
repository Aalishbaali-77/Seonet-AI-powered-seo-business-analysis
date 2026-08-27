"use client";

import { Suspense } from "react";

import { LeadDiscoverPage } from "@/features/leads/LeadDiscoverPage";

export default function Page() {
  return (
    <Suspense>
      <LeadDiscoverPage />
    </Suspense>
  );
}
