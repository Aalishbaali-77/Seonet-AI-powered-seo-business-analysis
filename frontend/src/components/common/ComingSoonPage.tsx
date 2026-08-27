"use client";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/feedback/EmptyState";

export function ComingSoonPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <EmptyState
        title={`${title} is not enabled yet`}
        description="This module is part of the Seonet roadmap. The navigation is in place so the product can grow without fake data."
      />
    </>
  );
}
