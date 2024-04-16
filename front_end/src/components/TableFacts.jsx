import { Chip, Stack } from '@mui/material';

// What the parser actually made of the upload: encoding and delimiter are
// guessed, so they are shown rather than hidden.
export default function TableFacts({ summary, role }) {
  const delimiter = summary.delimiter === '\t' ? 'tab' : summary.delimiter;
  return (
    <Stack
      direction="row"
      spacing={1}
      useFlexGap
      component="ul"
      aria-label={`${role} file details`}
      sx={{ listStyle: 'none', p: 0, m: 0, flexWrap: 'wrap' }}
    >
      {[
        { label: role, color: 'primary', variant: 'outlined' },
        { label: summary.filename, mono: true },
        { label: `${summary.columns.length} columns` },
        { label: `${summary.row_count} rows${summary.truncated ? ' (truncated)' : ''}` },
        { label: `encoding ${summary.encoding}` },
        { label: `delimiter ${delimiter}` },
      ].map((chip) => (
        <li key={chip.label}>
          <Chip
            size="small"
            label={chip.label}
            color={chip.color}
            variant={chip.variant}
            className={chip.mono ? 'mono' : undefined}
          />
        </li>
      ))}
    </Stack>
  );
}
