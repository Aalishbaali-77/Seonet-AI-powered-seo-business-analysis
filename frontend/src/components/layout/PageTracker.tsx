"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

import { telemetryApi } from "@/services/domainApi";
import { useAppSelector } from "@/store/hooks";

export function PageTracker() {
  const pathname = usePathname();
  const tenantId = useAppSelector((state) => state.tenant.currentId);
  const last = useRef("");

  useEffect(() => {
    if (!tenantId || !pathname.startsWith("/app")) {
      return;
    }
    const key = `${tenantId}:${pathname}`;
    if (last.current === key) {
      return;
    }
    last.current = key;
    void telemetryApi.page({
      path: pathname,
      title: typeof document !== "undefined" ? document.title : "",
      referrer: typeof document !== "undefined" ? document.referrer : "",
    });
  }, [pathname, tenantId]);

  return null;
}
