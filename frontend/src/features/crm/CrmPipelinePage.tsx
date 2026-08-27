"use client";

import { Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { crmApi } from "@/services/domainApi";
import type { Pipeline, Stage } from "@/types/domain";

function asError(err: unknown, fallback: string) {
  return err instanceof Error ? err.message : fallback;
}

export function CrmPipelinePage() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [name, setName] = useState("");
  const [stageName, setStageName] = useState("");
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    const rows = await crmApi.pipelines();
    setPipelines(rows);
    setSelected((current) => current || rows.find((item) => item.is_default)?.id || rows[0]?.id || "");
  };

  useEffect(() => {
    void load()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (error && !pipelines.length) return <ErrorState message={error} onRetry={() => void load().catch((err: Error) => setError(err.message))} />;

  const pipeline = pipelines.find((item) => item.id === selected) ?? pipelines[0] ?? null;

  const saveStage = async (stage: Stage, patch: Partial<Stage>) => {
    if (!pipeline) return;
    try {
      await crmApi.updateStage(pipeline.id, stage.id, patch);
      await load();
    } catch (err) {
      setError(asError(err, "Unable to update stage."));
    }
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Pipelines"
        description="Named sales pipelines and stages for this workspace. Deals stay on stored stages. Funnel counts are stored deals, not a forecast."
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField size="small" label="New pipeline" value={name} onChange={(event) => setName(event.target.value)} />
        <Button
          variant="contained"
          onClick={async () => {
            if (!name.trim()) return;
            try {
              const created = await crmApi.createPipeline({ name: name.trim() });
              setName("");
              setSelected(created.id);
              await load();
            } catch (err) {
              setError(asError(err, "Unable to create pipeline."));
            }
          }}
        >
          Create
        </Button>
      </Stack>
      {!pipeline ? (
        <EmptyState title="No pipelines" description="A default Sales pipeline is created with the workspace." />
      ) : (
        <>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
            <TextField select size="small" label="Pipeline" value={pipeline.id} onChange={(event) => setSelected(event.target.value)} sx={{ minWidth: 220 }}>
              {pipelines.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.name}
                  {item.is_default ? " (default)" : ""}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              label="Name"
              value={pipeline.name}
              onChange={(event) => setPipelines(pipelines.map((item) => (item.id === pipeline.id ? { ...item, name: event.target.value } : item)))}
            />
            <Button
              onClick={async () => {
                try {
                  await crmApi.updatePipeline(pipeline.id, { name: pipeline.name });
                  await load();
                } catch (err) {
                  setError(asError(err, "Unable to rename pipeline."));
                }
              }}
            >
              Save name
            </Button>
            {!pipeline.is_default ? (
              <Button
                onClick={async () => {
                  try {
                    await crmApi.updatePipeline(pipeline.id, { is_default: true });
                    await load();
                  } catch (err) {
                    setError(asError(err, "Unable to set default pipeline."));
                  }
                }}
              >
                Make default
              </Button>
            ) : null}
            {!pipeline.is_default ? (
              <Button
                color="error"
                onClick={async () => {
                  try {
                    await crmApi.deletePipeline(pipeline.id);
                    setSelected("");
                    await load();
                  } catch (err) {
                    setError(asError(err, "Unable to delete pipeline."));
                  }
                }}
              >
                Delete
              </Button>
            ) : null}
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField size="small" label="New stage" value={stageName} onChange={(event) => setStageName(event.target.value)} />
            <Button
              onClick={async () => {
                if (!stageName.trim()) return;
                try {
                  await crmApi.createStage(pipeline.id, { name: stageName.trim(), order: pipeline.stages.length });
                  setStageName("");
                  await load();
                } catch (err) {
                  setError(asError(err, "Unable to add stage."));
                }
              }}
            >
              Add stage
            </Button>
          </Stack>
          {pipeline.stages.map((stage) => (
            <Paper key={stage.id} variant="outlined" sx={{ p: 1.5 }}>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ alignItems: { md: "center" } }}>
                <TextField
                  size="small"
                  label="Stage"
                  value={stage.name}
                  onChange={(event) =>
                    setPipelines(
                      pipelines.map((item) =>
                        item.id === pipeline.id
                          ? { ...item, stages: item.stages.map((row) => (row.id === stage.id ? { ...row, name: event.target.value } : row)) }
                          : item,
                      ),
                    )
                  }
                />
                <TextField
                  size="small"
                  type="number"
                  label="Order"
                  value={stage.order}
                  onChange={(event) =>
                    setPipelines(
                      pipelines.map((item) =>
                        item.id === pipeline.id
                          ? { ...item, stages: item.stages.map((row) => (row.id === stage.id ? { ...row, order: Number(event.target.value) } : row)) }
                          : item,
                      ),
                    )
                  }
                  sx={{ width: 100 }}
                />
                <TextField
                  select
                  size="small"
                  label="Outcome"
                  value={stage.is_won ? "won" : stage.is_lost ? "lost" : "open"}
                  onChange={(event) => {
                    const value = event.target.value;
                    void saveStage(stage, { is_won: value === "won", is_lost: value === "lost" });
                  }}
                  sx={{ minWidth: 140 }}
                >
                  <MenuItem value="open">Open</MenuItem>
                  <MenuItem value="won">Won</MenuItem>
                  <MenuItem value="lost">Lost</MenuItem>
                </TextField>
                <Button onClick={() => void saveStage(stage, { name: stage.name, order: stage.order })}>Save</Button>
                <Button color="error" onClick={() => void crmApi.deleteStage(pipeline.id, stage.id).then(load).catch((err: Error) => setError(err.message))}>
                  Delete
                </Button>
              </Stack>
            </Paper>
          ))}
          <Typography color="text.secondary">Deleting a stage or pipeline fails while deals still sit on it.</Typography>
        </>
      )}
    </Stack>
  );
}
