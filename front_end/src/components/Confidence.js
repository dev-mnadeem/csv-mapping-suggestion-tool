import React from 'react';
import { Box, LinearProgress, Tooltip, Typography } from '@mui/material';
import { bandFor } from '../config';

const PERCENT = 100;

export default function Confidence({ value, rationale }) {
  const band = bandFor(value);
  return (
    <Tooltip title={rationale || ''} placement="top" arrow>
      <Box sx={{ minWidth: 148 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="body2" fontWeight={650}>
            {Math.round(value * PERCENT)}%
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {band.label}
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          color={band.color}
          value={value * PERCENT}
          sx={{ height: 6, borderRadius: 3 }}
        />
      </Box>
    </Tooltip>
  );
}
