"use client";

import { MarketSignalsPage } from "@/features/growth/MarketPages";

export default function Page() {
  return (
    <MarketSignalsPage
      title="Customer segments"
      kinds={[
        { value: "target_category", label: "Target category" },
        { value: "growth_signals", label: "Growth signals" },
      ]}
    />
  );
}
