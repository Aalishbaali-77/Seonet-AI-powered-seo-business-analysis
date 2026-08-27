"use client";

import { Box, Paper, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

export type DataColumn<T> = {
  key: string;
  label: string;
  hideOnMobile?: boolean;
  render: (row: T) => ReactNode;
};

export function ResponsiveDataList<T extends { id: string }>({
  rows,
  columns,
  onRowClick,
  cardTitle,
}: {
  rows: T[];
  columns: DataColumn<T>[];
  onRowClick?: (row: T) => void;
  cardTitle: (row: T) => ReactNode;
}) {
  return (
    <>
      <Stack spacing={1.5} sx={{ display: { xs: "flex", md: "none" } }}>
        {rows.map((row) => (
          <Paper
            key={row.id}
            variant="outlined"
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            sx={{ p: 2, cursor: onRowClick ? "pointer" : "default" }}
          >
            <Typography variant="h5" sx={{ mb: 1 }}>
              {cardTitle(row)}
            </Typography>
            <Stack spacing={0.75}>
              {columns
                .filter((column) => !column.hideOnMobile)
                .map((column) => (
                  <Box key={column.key} sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      {column.label}
                    </Typography>
                    <Box sx={{ textAlign: "right" }}>{column.render(row)}</Box>
                  </Box>
                ))}
            </Stack>
          </Paper>
        ))}
      </Stack>
      <Box sx={{ display: { xs: "none", md: "block" }, overflowX: "auto" }}>
        <Box component="table" sx={{ width: "100%", borderCollapse: "collapse", minWidth: 640 }}>
          <Box component="thead">
            <Box component="tr">
              {columns.map((column) => (
                <Box
                  component="th"
                  key={column.key}
                  sx={{ textAlign: "left", p: 1.5, borderBottom: 1, borderColor: "divider", color: "text.secondary", fontSize: 12 }}
                >
                  {column.label}
                </Box>
              ))}
            </Box>
          </Box>
          <Box component="tbody">
            {rows.map((row) => (
              <Box
                component="tr"
                key={row.id}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                sx={{ cursor: onRowClick ? "pointer" : "default", "&:hover": { bgcolor: "action.hover" } }}
              >
                {columns.map((column) => (
                  <Box component="td" key={column.key} sx={{ p: 1.5, borderBottom: 1, borderColor: "divider", verticalAlign: "top" }}>
                    {column.render(row)}
                  </Box>
                ))}
              </Box>
            ))}
          </Box>
        </Box>
      </Box>
    </>
  );
}
