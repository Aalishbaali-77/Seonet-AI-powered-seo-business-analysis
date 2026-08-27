"use client";

import { useEffect } from "react";

import { DEFAULT_FAVICON, resolveFaviconSrc } from "@/components/branding/BrandMark";
import { useAppSelector } from "@/store/hooks";

function upsertLink(rel: string, href: string, extra?: Record<string, string>) {
  let link = document.querySelector(`link[data-sipulse-brand="${rel}"]`) as HTMLLinkElement | null;
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("data-sipulse-brand", rel);
    document.head.appendChild(link);
  }
  link.rel = rel;
  link.href = href;
  if (extra) {
    Object.entries(extra).forEach(([key, value]) => link?.setAttribute(key, value));
  }
}

export function BrandingApplier() {
  const branding = useAppSelector((state) => state.ui.branding);

  useEffect(() => {
    const title = branding.tagline ? `${branding.product_name} — ${branding.tagline}` : branding.product_name;
    document.title = title;

    const description = document.querySelector('meta[name="description"]');
    if (description && branding.description) {
      description.setAttribute("content", branding.description);
    }

    const icon = resolveFaviconSrc(branding) || DEFAULT_FAVICON;
    upsertLink("icon", icon);
    const touch = branding.app_icon_url || branding.logo_mark_url;
    if (touch) {
      upsertLink("apple-touch-icon", touch);
    }

    document.documentElement.style.setProperty("--sipulse-primary", branding.primary_color);
    document.documentElement.style.setProperty("--sipulse-secondary", branding.secondary_color);
  }, [branding]);

  return null;
}
