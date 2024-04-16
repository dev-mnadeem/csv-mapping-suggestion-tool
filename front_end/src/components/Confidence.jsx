import { Box, LinearProgress, Typography } from '@mui/material';
import { bandFor } from '../config';

const PERCENT = 100;

export default function Confidence({ value }) {
  if (value === null) {
    return (
      <Typography variant="body2" color="text.secondary">
        not scored
      </Typography>
    );
  }
  const band = bandFor(value);
  const percent = Math.round(value * PERCENT);
  return (
    <Box sx={{ minWidth: 132 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography variant="body2" className="mono" sx={{ fontWeight: 600 }}>
          {percent}%
        </Typography>
        <Typography variant="body2" color={`${band.color}.main`}>
          {band.label}
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        color={band.color}
        value={value * PERCENT}
        aria-label={`confidence ${percent}%, ${band.label}`}
        sx={{ height: 6, borderRadius: 3, bgcolor: '#ece7da' }}
      />
    </Box>
  );
}
