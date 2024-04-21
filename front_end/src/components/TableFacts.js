import React from 'react';
import { Chip, Stack } from '@mui/material';

// What the parser actually made of the upload: encoding and delimiter are
// guessed, so they are shown rather than hidden.
export default function TableFacts({ summary, role }) {
  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      <Chip size="small" label={role} color="primary" variant="outlined" />
      <Chip size="small" label={summary.filename} className="mono" />
      <Chip size="small" label={`${summary.columns.length} columns`} />
      <Chip size="small" label={`${summary.row_count} rows`} />
      <Chip size="small" label={`encoding ${summary.encoding}`} />
      <Chip
        size="small"
        label={`delimiter ${summary.delimiter === '\t' ? 'tab' : summary.delimiter}`}
      />
    </Stack>
  );
}
