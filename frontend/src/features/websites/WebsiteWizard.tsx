"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Box, Button, Stack, Step, StepLabel, Stepper, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useAuditSession } from "@/features/websites/auditSession";
import { websiteApi } from "@/services/domainApi";

const schema = z.object({
  url: z.string().url("Enter a valid URL including https://"),
  business_name: z.string().min(2, "Business name is required"),
  industry: z.string().optional(),
  description: z.string().optional(),
  target_markets: z.string().optional(),
  keywords: z.string().optional(),
  competitors: z.string().optional(),
  max_pages: z.string().optional(),
});

type Values = z.infer<typeof schema>;

const steps = ["Website URL", "Business", "Target market", "Keywords", "Competitors", "Audit config", "Review", "Start audit"];

function csv(value?: string) {
  return (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function WebsiteWizard() {
  const { start } = useAuditSession();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { url: "https://", max_pages: "20" },
  });
  const values = form.watch();

  const next = async () => {
    if (step === 0) {
      const ok = await form.trigger("url");
      if (!ok) return;
    }
    if (step === 1) {
      const ok = await form.trigger("business_name");
      if (!ok) return;
    }
    setStep((value) => Math.min(value + 1, steps.length - 1));
  };

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      const site = await websiteApi.create({
        url: values.url,
        business_name: values.business_name,
        industry: values.industry ?? "",
        description: values.description ?? "",
        target_markets: csv(values.target_markets),
        keywords: csv(values.keywords),
        competitors: csv(values.competitors),
        audit_config: { max_pages: Number(values.max_pages || 20) },
        name: values.business_name,
      });
      const created = await websiteApi.startAudit(site.id);
      start({ jobId: created.id, websiteId: site.id, websiteLabel: values.business_name || site.domain });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start audit.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h1">Add website</Typography>
      <Stepper activeStep={step} alternativeLabel={!false} sx={{ display: { xs: "none", md: "flex" } }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      <Typography sx={{ display: { md: "none" } }}>
        Step {step + 1} of {steps.length}: {steps[step]}
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {step === 0 ? <TextField label="Website URL" {...form.register("url")} error={Boolean(form.formState.errors.url)} helperText={form.formState.errors.url?.message} /> : null}
      {step === 1 ? (
        <Stack spacing={2}>
          <TextField label="Business name" {...form.register("business_name")} error={Boolean(form.formState.errors.business_name)} helperText={form.formState.errors.business_name?.message} />
          <TextField label="Industry" {...form.register("industry")} />
          <TextField label="Description" multiline minRows={3} {...form.register("description")} />
        </Stack>
      ) : null}
      {step === 2 ? <TextField label="Target markets" helperText="Comma-separated cities or regions" {...form.register("target_markets")} /> : null}
      {step === 3 ? <TextField label="Keywords" helperText="Comma-separated" {...form.register("keywords")} /> : null}
      {step === 4 ? <TextField label="Competitors" helperText="Comma-separated domains" {...form.register("competitors")} /> : null}
      {step === 5 ? <TextField label="Max pages" type="number" {...form.register("max_pages")} /> : null}
      {step >= 6 ? (
        <Box>
          <Typography variant="h5" gutterBottom>
            Review
          </Typography>
          <Typography>URL: {values.url}</Typography>
          <Typography>Business: {values.business_name}</Typography>
          <Typography>Markets: {values.target_markets || "—"}</Typography>
          <Typography>Keywords: {values.keywords || "—"}</Typography>
        </Box>
      ) : null}
      <Stack direction="row" spacing={2}>
        <Button disabled={step === 0} onClick={() => setStep((value) => value - 1)}>
          Back
        </Button>
        {step < 7 ? (
          <Button variant="contained" onClick={() => void next()}>
            Continue
          </Button>
        ) : (
          <Button variant="contained" onClick={() => void submit()} disabled={saving}>
            {saving ? "Starting…" : "Start audit"}
          </Button>
        )}
      </Stack>
    </Stack>
  );
}
