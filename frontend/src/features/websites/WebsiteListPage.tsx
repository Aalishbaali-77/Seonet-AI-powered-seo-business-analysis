"use client";

import AddIcon from "@mui/icons-material/Add";
import { Button, Stack } from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { RowMenu } from "@/components/common/RowMenu";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { useAuditSession } from "@/features/websites/auditSession";
import { websiteApi } from "@/services/domainApi";
import type { Website } from "@/types/domain";

export function WebsiteListPage() {
  const router = useRouter();
  const [items, setItems] = useState<Website[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const { start, job } = useAuditSession();
  const confirm = useConfirm();

  const load = () =>
    websiteApi
      .listAll()
      .then((rows) => {
        setItems(rows);
        setStatus("ready");
        setError("");
      })
      .catch((err: Error) => {
        setError(err.message);
        setStatus("error");
      });

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (job?.status === "COMPLETED") {
      void load();
    }
  }, [job?.status]);

  const runAudit = async (site: Website) => {
    try {
      const created = await websiteApi.startAudit(site.id);
      start({ jobId: created.id, websiteId: site.id, websiteLabel: site.name || site.domain });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start audit.");
    }
  };

  const patchStatus = async (site: Website, next: "active" | "archived") => {
    try {
      const updated = await websiteApi.update(site.id, { status: next });
      setItems((current) => current.map((item) => (item.id === site.id ? updated : item)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update website.");
    }
  };

  const removeSite = async (site: Website) => {
    const ok = await confirm({
      title: "Remove website",
      description: `${site.domain} and its audits and issues will be deleted. This cannot be undone.`,
      confirmLabel: "Remove",
    });
    if (!ok) {
      return;
    }
    try {
      await websiteApi.delete(site.id);
      setItems((current) => current.filter((item) => item.id !== site.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove website.");
    }
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Websites"
        description="Audit properties for SEO, AEO, GEO, performance, and accessibility."
        actions={
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => router.push("/app/websites/new")}>
            Add website
          </Button>
        }
      />
      {status === "loading" ? <LoadingState /> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {status === "ready" && items.length === 0 && !error ? (
        <EmptyState
          title="No websites yet"
          description="Add your first website to start your SIPulse intelligence journey."
          actionLabel="Add Website"
          onAction={() => router.push("/app/websites/new")}
        />
      ) : null}
      {status === "ready" && items.length > 0 ? (
        <ResponsiveDataList
          rows={items}
          cardTitle={(site) => site.name || site.domain}
          onRowClick={(site) => router.push(`/app/websites/${site.id}`)}
          columns={[
            { key: "website", label: "Website", render: (site) => site.domain },
            { key: "business", label: "Business", hideOnMobile: true, render: (site) => site.business_name || "—" },
            { key: "score", label: "Score", render: (site) => site.last_audit?.overall_score ?? "—" },
            { key: "seo", label: "SEO", hideOnMobile: true, render: (site) => site.last_audit?.scores.technical_seo ?? "—" },
            { key: "aeo", label: "AEO", hideOnMobile: true, render: (site) => site.last_audit?.scores.aeo ?? "—" },
            { key: "geo", label: "GEO", hideOnMobile: true, render: (site) => site.last_audit?.scores.geo ?? "—" },
            {
              key: "perf",
              label: "Performance",
              hideOnMobile: true,
              render: (site) => site.last_audit?.scores.performance ?? "—",
            },
            {
              key: "last",
              label: "Last audit",
              hideOnMobile: true,
              render: (site) => (site.last_audit?.completed_at ? new Date(site.last_audit.completed_at).toLocaleDateString() : "—"),
            },
            { key: "status", label: "Status", render: (site) => <StatusChip value={site.status} /> },
            {
              key: "actions",
              label: "Actions",
              render: (site) => {
                const audited = Boolean(site.last_audit);
                const archived = site.status === "archived";
                return (
                  <RowMenu
                    label={`Actions for ${site.domain}`}
                    items={[
                      { label: "Open", onClick: () => router.push(`/app/websites/${site.id}`) },
                      {
                        label: audited ? "Re-audit" : "Run audit",
                        disabled: archived,
                        onClick: () => void runAudit(site),
                      },
                      {
                        label: "Open report",
                        disabled: !audited,
                        onClick: () => router.push(`/app/audits/${site.last_audit?.id}/report`),
                      },
                      {
                        label: "Issues",
                        disabled: !audited,
                        onClick: () => router.push(`/app/websites/${site.id}/issues`),
                      },
                      { label: "Keyword ranks", onClick: () => router.push(`/app/websites/${site.id}/keywords`) },
                      {
                        label: "Performance",
                        disabled: !audited,
                        onClick: () => router.push(`/app/websites/${site.id}/performance`),
                      },
                      {
                        label: "Recommendations",
                        disabled: !audited,
                        onClick: () => router.push(`/app/websites/${site.id}/recommendations`),
                      },
                      { label: "History", onClick: () => router.push(`/app/websites/${site.id}/history`) },
                      {
                        label: archived ? "Restore" : "Archive",
                        onClick: () => void patchStatus(site, archived ? "active" : "archived"),
                      },
                      { label: "Remove", danger: true, onClick: () => void removeSite(site) },
                    ]}
                  />
                );
              },
            },
          ]}
        />
      ) : null}
    </Stack>
  );
}
