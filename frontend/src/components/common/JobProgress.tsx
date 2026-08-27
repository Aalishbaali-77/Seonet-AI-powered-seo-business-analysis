"use client";

import { useEffect, useRef } from "react";

import { JobProgressPanel } from "@/components/common/JobProgressPanel";
import { useJobProgress } from "@/features/websites/useJobProgress";
import type { Job } from "@/types/domain";

export function JobProgress({ jobId, onComplete }: { jobId: string; onComplete?: (job: Job) => void }) {
  const { job, error } = useJobProgress(jobId);
  const notified = useRef(false);

  useEffect(() => {
    if (!job || !onComplete || notified.current) {
      return;
    }
    if (job.status === "COMPLETED" || job.status === "FAILED") {
      notified.current = true;
      onComplete(job);
    }
  }, [job, onComplete]);

  return <JobProgressPanel job={job} error={error} />;
}
