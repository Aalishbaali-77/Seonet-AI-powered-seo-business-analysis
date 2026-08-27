"use client";

import { Box, Button, Dialog, DialogActions, DialogContent, Tooltip, Typography } from "@mui/material";
import { useRouter } from "next/navigation";

import { ScoreRing } from "@/components/common/ScoreRing";
import { JobProgressPanel } from "@/components/common/JobProgressPanel";
import { useAuditSession } from "@/features/websites/auditSession";

function liveLabel(kind: string) {
  if (kind === "import_commerce" || kind === "import_markets") return "CSV import";
  if (kind === "collect_markets") return "Market collect";
  if (kind === "sync_commerce") return "Store sync";
  if (kind === "analyze_business") return "Business analysis";
  if (kind === "analyze_market") return "Market analysis";
  if (kind === "apply_audit_fixes") return "Apply recommended fixes";
  if (kind === "check_keyword_ranks") return "Keyword ranks";
  if (kind === "discover_leads") return "Lead discovery";
  return "Live audit";
}

function doneHint(kind: string, complete: boolean, failed: boolean, percent: number) {
  if (complete) return `${liveLabel(kind)} complete — view results`;
  if (failed) return `${liveLabel(kind)} failed — view details`;
  return `${liveLabel(kind)} ${percent}%`;
}

export function AuditProgressHost() {
  const router = useRouter();
  const { session, dialogOpen, job, error, hideToBackground, reopen, dismiss } = useAuditSession();
  const kind = session?.kind || job?.job_type || "run_audit";
  const running = Boolean(job && job.status !== "COMPLETED" && job.status !== "FAILED" && job.status !== "CANCELLED");
  const pending = Boolean(session && !job);
  const blocking = running || pending;
  const complete = job?.status === "COMPLETED";
  const failed = job?.status === "FAILED";
  const auditId = typeof job?.result.audit_id === "string" ? job.result.audit_id : "";
  const percent = complete ? 100 : Math.min(job?.progress ?? 0, 99);
  const showFab = Boolean(session) && !dialogOpen;
  const href = session?.href;
  const viewLabel = kind === "check_keyword_ranks" ? "View keyword ranks" : kind === "apply_audit_fixes" ? "View fix progress" : kind === "import_commerce" || kind === "import_markets" || kind === "collect_markets" || kind === "analyze_market" ? "View market brief" : kind === "sync_commerce" || kind === "analyze_business" ? "Open e-commerce" : kind === "discover_leads" ? "Open leads" : session?.websiteId ? "View website" : href ? "Open" : "";

  return (
    <>
      <Dialog
        open={dialogOpen}
        onClose={(_event, reason) => {
          if (blocking && (reason === "backdropClick" || reason === "escapeKeyDown")) {
            return;
          }
          if (blocking) {
            hideToBackground();
            return;
          }
          dismiss();
        }}
        fullWidth
        maxWidth="xs"
        slotProps={{
          paper: {
            sx: {
              borderRadius: 4,
              overflow: "hidden",
              backgroundImage: (theme) =>
                theme.palette.mode === "dark"
                  ? "linear-gradient(180deg, rgba(46,196,182,0.12) 0%, transparent 42%)"
                  : "linear-gradient(180deg, rgba(46,196,182,0.14) 0%, transparent 42%)",
            },
          },
        }}
      >
        <DialogContent sx={{ px: 3, pt: 3, pb: 1 }}>
          <Typography variant="subtitle2" color="secondary" sx={{ mb: 0.5 }}>
            {complete ? "Complete" : failed ? "Failed" : liveLabel(kind)}
          </Typography>
          <Typography variant="h3" sx={{ mb: 2.5 }}>
            {session?.title || "Workspace job"}
          </Typography>
          <JobProgressPanel job={job} error={error} kind={kind} />
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2, gap: 1 }}>
          {blocking ? (
            <Button onClick={hideToBackground}>Continue in background</Button>
          ) : (
            <>
              <Button onClick={dismiss}>Close</Button>
              {href ? (
                <Button
                  onClick={() => {
                    dismiss();
                    router.push(href);
                  }}
                >
                  {viewLabel || "Open"}
                </Button>
              ) : null}
              {complete && auditId ? (
                <Button
                  variant="contained"
                  onClick={() => {
                    dismiss();
                    router.push(`/app/audits/${auditId}/report`);
                  }}
                >
                  Open report
                </Button>
              ) : null}
            </>
          )}
        </DialogActions>
      </Dialog>
      {showFab ? (
        <Tooltip title={doneHint(kind, complete, failed, percent)} placement="left">
          <Box
            component="button"
            type="button"
            aria-label="Show job progress"
            onClick={reopen}
            sx={{
              position: "fixed",
              right: { xs: 16, md: 24 },
              bottom: { xs: 16, md: 24 },
              zIndex: 1250,
              width: 76,
              height: 76,
              border: 0,
              borderRadius: "50%",
              cursor: "pointer",
              p: 0,
              bgcolor: "background.paper",
              boxShadow: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              "@keyframes sipulseFab": {
                "0%, 100%": { boxShadow: "0 8px 24px rgba(20,138,153,0.28)" },
                "50%": { boxShadow: "0 8px 28px rgba(20,138,153,0.5)" },
              },
              animation: blocking ? "sipulseFab 2s ease-in-out infinite" : "none",
            }}
          >
            <ScoreRing
              value={job ? percent : null}
              size={64}
              stroke={6}
              label="Job progress"
              tone={failed ? "error" : "progress"}
              suffix={complete || failed ? undefined : "%"}
              icon={complete ? "check" : failed ? "error" : undefined}
            />
          </Box>
        </Tooltip>
      ) : null}
    </>
  );
}
