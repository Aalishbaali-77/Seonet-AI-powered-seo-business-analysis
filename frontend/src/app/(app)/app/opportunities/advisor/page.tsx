"use client";

import { AdvisorPanel } from "@/features/growth/AdvisorPanel";

export default function Page() {
  return (
    <AdvisorPanel
      domain="opportunity"
      title="AI opportunity advisor"
      description="Uses recorded growth opportunities. CRM deals are not mixed in."
    />
  );
}
