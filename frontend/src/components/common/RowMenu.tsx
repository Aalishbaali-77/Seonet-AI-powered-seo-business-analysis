"use client";

import MoreVertIcon from "@mui/icons-material/MoreVert";
import { IconButton, Menu, MenuItem } from "@mui/material";
import { useState } from "react";

export type RowMenuItem = {
  label: string;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
};

export function RowMenu({ items, label = "Open actions" }: { items: RowMenuItem[]; label?: string }) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  return (
    <>
      <IconButton
        size="small"
        aria-label={label}
        onClick={(event) => {
          event.stopPropagation();
          setAnchor(event.currentTarget);
        }}
      >
        <MoreVertIcon fontSize="small" />
      </IconButton>
      <Menu
        anchorEl={anchor}
        open={Boolean(anchor)}
        onClose={() => setAnchor(null)}
        onClick={(event) => event.stopPropagation()}
      >
        {items.map((item) => (
          <MenuItem
            key={item.label}
            disabled={item.disabled}
            onClick={() => {
              setAnchor(null);
              item.onClick();
            }}
            sx={item.danger ? { color: "error.main" } : undefined}
          >
            {item.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
