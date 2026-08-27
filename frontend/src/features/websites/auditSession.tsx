"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { useJobProgress } from "@/features/websites/useJobProgress";
import type { Job } from "@/types/domain";

export type JobSession = {
  jobId: string;
  kind: string;
  title: string;
  href?: string;
  websiteId?: string;
};

export type AuditSession = JobSession & { websiteLabel?: string };

type StartInput = JobSession | { jobId: string; websiteId: string; websiteLabel: string };

type JobSessionContextValue = {
  session: JobSession | null;
  dialogOpen: boolean;
  job: Job | null;
  error: string;
  start: (session: StartInput) => void;
  hideToBackground: () => void;
  reopen: () => void;
  dismiss: () => void;
};

const STORAGE_KEY = "sipulse.auditJob";
const JobSessionContext = createContext<JobSessionContextValue | null>(null);

function asSession(input: StartInput): JobSession {
  if ("kind" in input && input.kind) {
    return input;
  }
  const audit = input as { jobId: string; websiteId: string; websiteLabel: string };
  return {
    jobId: audit.jobId,
    kind: "run_audit",
    title: audit.websiteLabel,
    href: `/app/websites/${audit.websiteId}`,
    websiteId: audit.websiteId,
  };
}

function readStoredSession(): JobSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as StartInput & { websiteLabel?: string };
    if (!parsed?.jobId) {
      return null;
    }
    return asSession(parsed as StartInput);
  } catch {
    return null;
  }
}

export function AuditSessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<JobSession | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const { job, error } = useJobProgress(session?.jobId ?? null);

  useEffect(() => {
    setSession(readStoredSession());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    if (session) {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } else {
      window.sessionStorage.removeItem(STORAGE_KEY);
    }
  }, [hydrated, session]);

  useEffect(() => {
    if (!session || dialogOpen) {
      return;
    }
    if (job?.status === "COMPLETED" || job?.status === "FAILED") {
      setDialogOpen(true);
    }
  }, [dialogOpen, job?.status, session]);

  const start = useCallback((next: StartInput) => {
    setSession(asSession(next));
    setDialogOpen(true);
  }, []);

  const hideToBackground = useCallback(() => {
    setDialogOpen(false);
  }, []);

  const reopen = useCallback(() => {
    setDialogOpen(true);
  }, []);

  const dismiss = useCallback(() => {
    setDialogOpen(false);
    setSession(null);
  }, []);

  const value = useMemo(
    () => ({ session, dialogOpen, job, error, start, hideToBackground, reopen, dismiss }),
    [session, dialogOpen, job, error, start, hideToBackground, reopen, dismiss],
  );

  return <JobSessionContext.Provider value={value}>{children}</JobSessionContext.Provider>;
}

export function useAuditSession() {
  const context = useContext(JobSessionContext);
  if (!context) {
    throw new Error("useAuditSession must be used within AuditSessionProvider");
  }
  return context;
}

export const useJobSession = useAuditSession;
