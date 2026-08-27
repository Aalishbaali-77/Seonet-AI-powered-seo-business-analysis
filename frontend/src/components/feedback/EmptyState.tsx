"use client";

import { Box, Button, Paper, Typography } from "@mui/material";

type EmptyStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function EmptyState({ title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: { xs: 3, md: 5 },
        textAlign: "center",
        borderStyle: "dashed",
      }}
    >
      <Typography variant="h4" gutterBottom>
        {title}
      </Typography>
      <Typography color="text.secondary" sx={{ maxWidth: 480, mx: "auto", mb: 2 }}>
        {description}
      </Typography>
      {actionLabel && onAction ? (
        <Button variant="contained" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </Paper>
  );
}
