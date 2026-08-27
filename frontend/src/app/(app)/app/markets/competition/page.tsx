"use client";

import { MarketSignalsPage } from "@/features/growth/MarketPages";

export default function Page() {
  return (
    <MarketSignalsPage
      title="Competition"
      kinds={[
        { value: "competition_gap", label: "Competition gap" },
        { value: "business_density", label: "Business density" },
      ]}
    />
  );
}
