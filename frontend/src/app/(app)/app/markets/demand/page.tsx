"use client";

import { MarketSignalsPage } from "@/features/growth/MarketPages";

export default function Page() {
  return (
    <MarketSignalsPage
      title="Demand intelligence"
      kinds={[
        { value: "demand", label: "Demand" },
        { value: "search_interest", label: "Search interest" },
        { value: "purchasing_power", label: "Purchasing power" },
        { value: "population", label: "Population" },
      ]}
    />
  );
}
