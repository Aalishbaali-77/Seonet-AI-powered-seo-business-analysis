"use client";

import { JobProgressPanel } from "@/components/common/JobProgressPanel";
import { useJobProgress } from "@/features/websites/useJobProgress";

export function AuditJobProgress({ job, error }: { job: Parameters<typeof JobProgressPanel>[0]["job"]; error?: string }) {
  return <JobProgressPanel job={job} error={error} />;
}

export function AuditJobTracker({ jobId }: { jobId: string | null }) {
  const { job, error } = useJobProgress(jobId);
  return <JobProgressPanel job={job} error={error} />;
}
