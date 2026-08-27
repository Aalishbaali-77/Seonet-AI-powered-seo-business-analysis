"use client";

import { AdvisorPanel } from "@/features/growth/AdvisorPanel";

export default function Page() {
  return (
    <AdvisorPanel
      domain="market"
      title="AI market advisor"
      description="Uses stored commerce and ingested market signals. Citations stay facts. City names without signals are not graded."
    />
  );
}
