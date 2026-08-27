"use client";

import type { ReactNode } from "react";
import { Box, Typography } from "@mui/material";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
};

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: { xs: "column", md: "row" },
        alignItems: { md: "flex-end" },
        justifyContent: "space-between",
        gap: 2,
        mb: 3,
      }}
    >
      <Box>
        {eyebrow ? (
          <Typography variant="subtitle2" color="secondary" gutterBottom>
            {eyebrow}
          </Typography>
        ) : null}
        <Typography variant="h1">{title}</Typography>
        {description ? (
          <Typography color="text.secondary" sx={{ mt: 0.75, maxWidth: 640 }}>
            {description}
          </Typography>
        ) : null}
      </Box>
      {actions}
    </Box>
  );
}
