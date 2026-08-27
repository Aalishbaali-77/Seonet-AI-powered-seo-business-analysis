"use client";

import { Skeleton, Stack } from "@mui/material";

export function LoadingState({ rows = 3 }: { rows?: number }) {
  return (
    <Stack spacing={2} aria-busy="true" aria-live="polite">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} variant="rounded" height={88} />
      ))}
    </Stack>
  );
}
