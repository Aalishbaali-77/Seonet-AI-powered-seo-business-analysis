"use client";

import { AdvisorPanel } from "@/features/growth/AdvisorPanel";

export default function Page() {
  return (
    <AdvisorPanel
      domain="business"
      title="AI business advisor"
      description="Advice is grounded in stored orders, product lines, served cities, and expansion evidence. The model is not allowed to invent revenue or city conversion rates."
    />
  );
}
