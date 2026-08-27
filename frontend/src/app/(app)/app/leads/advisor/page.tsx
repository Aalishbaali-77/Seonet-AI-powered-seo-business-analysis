"use client";

import { AdvisorPanel } from "@/features/growth/AdvisorPanel";

export default function Page() {
  return (
    <AdvisorPanel
      domain="lead"
      title="AI lead advisor"
      description="Uses stored lead counts and completeness scores. Contact details are not invented."
    />
  );
}
