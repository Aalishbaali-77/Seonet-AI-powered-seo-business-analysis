"use client";

import { Button, Stack } from "@mui/material";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { useJobSession } from "@/features/websites/auditSession";
import { websiteApi } from "@/services/domainApi";

export function WebsiteAuditProgressPage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const jobId = search.get("job");
  const { start, job } = useJobSession();
  const auditId = typeof job?.result.audit_id === "string" ? job.result.audit_id : "";
  const finished = job?.status === "COMPLETED" || job?.status === "FAILED";

  useEffect(() => {
    if (!jobId) {
      return;
    }
    void websiteApi
      .get(params.id)
      .then((site) => {
        start({
          jobId,
          kind: "run_audit",
          title: site.name || site.domain,
          href: `/app/websites/${params.id}`,
          websiteId: params.id,
        });
      })
      .catch(() => {
        start({ jobId, kind: "run_audit", title: "Website audit", href: `/app/websites/${params.id}`, websiteId: params.id });
      });
  }, [jobId, params.id, start]);

  if (!jobId) {
    return <PageHeader title="Audit" description="Start an audit from the website page to track live job progress." />;
  }
  return (
    <Stack spacing={3}>
      <PageHeader title="Running audit" description="Live progress is in the dialog — the same one used for CSV import, store sync, and lead discovery." />
      {finished ? (
        <Stack direction="row" spacing={1}>
          <Button onClick={() => router.push(`/app/websites/${params.id}`)}>View website</Button>
          {job?.status === "COMPLETED" && auditId ? (
            <Button variant="contained" onClick={() => router.push(`/app/audits/${auditId}/report`)}>
              Open report
            </Button>
          ) : null}
        </Stack>
      ) : null}
    </Stack>
  );
}
