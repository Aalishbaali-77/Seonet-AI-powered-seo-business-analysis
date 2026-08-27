"use client";

import BusinessIcon from "@mui/icons-material/Business";
import { FormControl, MenuItem, Select } from "@mui/material";

import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { tenantSelected } from "@/store/slices/tenantSlice";

export function TenantSwitcher() {
  const dispatch = useAppDispatch();
  const { items, currentId } = useAppSelector((state) => state.tenant);

  if (!items.length) {
    return null;
  }

  return (
    <FormControl size="small" sx={{ minWidth: { xs: 120, md: 180 } }}>
      <Select
        aria-label="Current workspace"
        value={currentId ?? items[0].id}
        onChange={(event) => {
          const value = event.target.value;
          window.localStorage.setItem("seonet.tenant", value);
          dispatch(tenantSelected(value));
        }}
        startAdornment={<BusinessIcon fontSize="small" sx={{ mr: 1, color: "text.secondary" }} />}
      >
        {items.map((tenant) => (
          <MenuItem key={tenant.id} value={tenant.id}>
            {tenant.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
