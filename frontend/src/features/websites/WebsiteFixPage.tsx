"use client";

import { Alert, Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { useAuditSession } from "@/features/websites/auditSession";
import { websiteApi } from "@/services/domainApi";
import type { AuditFixRun, FixPlanItem, IntelligenceCompare, WebsiteAccess } from "@/types/domain";

const KINDS = [
  { value: "wordpress", label: "WordPress application password" },
  { value: "cpanel", label: "cPanel FTP" },
  { value: "ftp", label: "FTP" },
  { value: "sftp", label: "SFTP / VPS" },
];

function asCompare(value: AuditFixRun["comparison"]): IntelligenceCompare | null {
  if (!value || typeof value !== "object" || !("available" in value) || !(value as IntelligenceCompare).available) {
    return null;
  }
  return value as IntelligenceCompare;
}

export function WebsiteFixPage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const { start, job } = useAuditSession();
  const seen = useRef("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [access, setAccess] = useState<WebsiteAccess | null>(null);
  const [connected, setConnected] = useState(false);
  const [kind, setKind] = useState("wordpress");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("");
  const [rootPath, setRootPath] = useState("public_html");
  const [wpUrl, setWpUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [plan, setPlan] = useState<{ audit_id: string; applicable: FixPlanItem[]; skipped: FixPlanItem[]; why: string } | null>(null);
  const [runs, setRuns] = useState<AuditFixRun[]>([]);
  const applying = Boolean(job && job.job_type === "apply_audit_fixes" && job.status !== "COMPLETED" && job.status !== "FAILED");

  const load = () =>
    Promise.all([websiteApi.get(params.id), websiteApi.access(params.id), websiteApi.fixRuns(params.id)])
      .then(([site, accessPayload, runPayload]) => {
        setConnected(accessPayload.connected);
        setAccess(accessPayload.access);
        if (accessPayload.access) {
          setKind(accessPayload.access.kind);
          setHost(accessPayload.access.host);
          setPort(String(accessPayload.access.port || ""));
          setRootPath(accessPayload.access.root_path || "public_html");
          setWpUrl(accessPayload.access.wp_url || site.url);
          setUsername(accessPayload.access.username);
        } else {
          setWpUrl(site.url);
        }
        setRuns(runPayload.results);
        const auditId = search.get("audit") || site.last_audit?.id;
        return websiteApi.fixPlan(params.id, auditId);
      })
      .then((next) => {
        setPlan(next);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));

  useEffect(() => {
    void load();
  }, [params.id]);

  useEffect(() => {
    if (job?.job_type !== "apply_audit_fixes") return;
    const key = `${job.id}:${job.status}`;
    if (seen.current === key) return;
    if (job.status === "COMPLETED" || job.status === "FAILED") {
      seen.current = key;
      void load();
      if (job.status === "FAILED") setError(job.error || "Apply failed.");
    }
  }, [job]);

  if (loading) return <LoadingState />;

  const latest = runs[0] ? asCompare(runs[0].comparison) : null;

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Connect access and apply recommended fixes"
        description="On demand only. Seonet does not change the live site until you connect WordPress, cPanel, FTP, or SFTP and confirm. The first completed audit is kept as the baseline. The follow-up crawl compares SEO, AEO, and GEO scores — not Google rankings."
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {note ? <Alert severity="success">{note}</Alert> : null}
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="h4">Website code access</Typography>
            <Alert severity="info">
              Credentials stay on the server. WordPress can update title and tagline. robots.txt, sitemap, canonical, Open Graph, and JSON-LD need FTP, SFTP, or cPanel file access. Performance and HTTPS are not auto-fixed.
            </Alert>
            <TextField select label="Access method" value={kind} onChange={(event) => setKind(event.target.value)}>
              {KINDS.map((item) => (
                <MenuItem key={item.value} value={item.value}>
                  {item.label}
                </MenuItem>
              ))}
            </TextField>
            {kind === "wordpress" ? (
              <TextField label="WordPress site URL" value={wpUrl} onChange={(event) => setWpUrl(event.target.value)} helperText="Must match the audited hostname. Use an application password, not the login password." />
            ) : (
              <>
                <TextField label="Host" value={host} onChange={(event) => setHost(event.target.value)} helperText="Public FTP or VPS hostname. Private IPs are rejected." />
                <TextField label="Port" value={port} onChange={(event) => setPort(event.target.value)} placeholder={kind === "sftp" ? "22" : "21"} />
                <TextField label="Document root" value={rootPath} onChange={(event) => setRootPath(event.target.value)} helperText="Usually public_html on cPanel." />
              </>
            )}
            <TextField label="Username" value={username} onChange={(event) => setUsername(event.target.value)} />
            <TextField label={kind === "wordpress" ? "Application password" : "Password"} type="password" value={password} onChange={(event) => setPassword(event.target.value)} helperText={access?.has_secret ? "Leave blank to keep the stored secret." : "Required to connect."} />
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                onClick={async () => {
                  try {
                    const saved = await websiteApi.saveAccess(params.id, {
                      kind,
                      host,
                      port,
                      root_path: rootPath,
                      wp_url: wpUrl,
                      username,
                      password,
                    });
                    setConnected(true);
                    setAccess(saved.access);
                    setPassword("");
                    setNote(saved.message);
                    setError("");
                    void load();
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Unable to connect.");
                  }
                }}
              >
                Test and save access
              </Button>
              {connected ? (
                <Button
                  onClick={async () => {
                    await websiteApi.removeAccess(params.id);
                    setConnected(false);
                    setAccess(null);
                    setNote("Access removed. The site was not changed.");
                  }}
                >
                  Disconnect
                </Button>
              ) : null}
            </Stack>
            <Typography color="text.secondary">{connected ? `Connected via ${access?.kind}.` : "Not connected. Recommendations stay a manual roadmap until you opt in."}</Typography>
          </Stack>
        </CardContent>
      </Card>
      {plan ? (
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="h4">Recommended fixes from the baseline audit</Typography>
              <Alert severity="info">{plan.why}</Alert>
              {plan.applicable.length ? (
                plan.applicable.map((item) => (
                  <Typography key={`${item.issue_id}-${item.code}`}>
                    Will apply: {item.title} ({item.via})
                  </Typography>
                ))
              ) : (
                <EmptyState title="Nothing auto-applicable" description="Connect file access or keep using the fix roadmap. Seonet will not invent copy or change server performance." />
              )}
              {plan.skipped.slice(0, 8).map((item) => (
                <Typography key={item.issue_id} color="text.secondary">
                  Manual: {item.title} — {item.reason}
                </Typography>
              ))}
              <Button
                variant="contained"
                disabled={!connected || applying || !plan.applicable.length}
                onClick={async () => {
                  try {
                    const created = await websiteApi.applyFixes(params.id, plan.audit_id);
                    start({
                      jobId: created.id,
                      kind: "apply_audit_fixes",
                      title: "Apply recommended fixes",
                      href: `/app/websites/${params.id}/fix?audit=${plan.audit_id}`,
                      websiteId: params.id,
                    });
                    setError("");
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Unable to apply fixes.");
                  }
                }}
              >
                Apply recommended fixes and re-check SEO / AEO / GEO
              </Button>
            </Stack>
          </CardContent>
        </Card>
      ) : null}
      {latest ? (
        <Stack spacing={2}>
          <Typography variant="h4">Progress after the last apply</Typography>
          <Alert severity="info">{latest.why}</Alert>
          <Typography>
            Issues {latest.before_issues} → {latest.after_issues}. Baseline audit kept. Follow-up audit stored separately.
          </Typography>
          <ResponsiveDataList
            rows={latest.rows.map((row) => ({ id: row.metric, ...row }))}
            cardTitle={(row) => row.metric}
            columns={[
              { key: "metric", label: "Score", render: (row) => row.metric },
              { key: "before", label: "Before fix", render: (row) => row.before ?? "—" },
              { key: "after", label: "After re-audit", render: (row) => row.after ?? "—" },
              { key: "delta", label: "Change", render: (row) => (row.delta == null ? "—" : row.delta > 0 ? `+${row.delta}` : String(row.delta)) },
            ]}
          />
          {latest.resolved_titles.length ? <Typography>Cleared findings: {latest.resolved_titles.join("; ")}</Typography> : null}
          <Stack direction="row" spacing={1}>
            <Button onClick={() => router.push(`/app/audits/${latest.baseline_audit_id}/report`)}>Open baseline report</Button>
            <Button variant="contained" onClick={() => router.push(`/app/audits/${latest.followup_audit_id}/report`)}>
              Open follow-up report
            </Button>
          </Stack>
        </Stack>
      ) : null}
    </Stack>
  );
}
