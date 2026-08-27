"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/services/apiClient";
import { jobApi } from "@/services/domainApi";
import type { Job } from "@/types/domain";

export function useJobProgress(jobId: string | null) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setError("");
      return;
    }
    let cancelled = false;
    const tick = async () => {
      try {
        const next = await jobApi.get(jobId);
        if (cancelled) {
          return;
        }
        setJob(next);
        setError("");
        if (next.status !== "COMPLETED" && next.status !== "FAILED" && next.status !== "CANCELLED") {
          window.setTimeout(() => {
            void tick();
          }, next.status === "QUEUED" || next.status === "PENDING" ? 700 : 1200);
        }
      } catch (err) {
        if (cancelled) {
          return;
        }
        const status = err instanceof ApiError ? err.status : 0;
        setError(err instanceof Error ? err.message : "Unable to read job progress.");
        if (status === 401 || status === 403) {
          return;
        }
        window.setTimeout(() => {
          void tick();
        }, 2000);
      }
    };
    void tick();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  return { job, error };
}
