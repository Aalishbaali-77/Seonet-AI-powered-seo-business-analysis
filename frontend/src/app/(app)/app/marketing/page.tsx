"use client";

import { Suspense } from "react";

import { CampaignListPage } from "@/features/marketing/MarketingPages";

export default function Page() {
  return (
    <Suspense>
      <CampaignListPage />
    </Suspense>
  );
}
