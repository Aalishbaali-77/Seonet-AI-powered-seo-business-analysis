"use client";

import { useParams } from "next/navigation";

import { DocsSite } from "@/features/docs/DocsSite";
import { findDoc } from "@/features/docs/content";

export default function DocsPage() {
  const params = useParams<{ slug?: string | string[] }>();
  const slug = Array.isArray(params.slug) ? params.slug : params.slug ? [params.slug] : [];
  const page = findDoc(slug);
  if (!page) {
    return (
      <DocsSite
        page={{
          slug: ["missing"],
          href: "/docs",
          title: "Page not found",
          description: "That documentation page does not exist.",
          group: "Getting started",
          blocks: [{ type: "p", text: "Use the sidebar to open a topic, or return to the user guide home." }],
        }}
      />
    );
  }
  return <DocsSite page={page} />;
}
