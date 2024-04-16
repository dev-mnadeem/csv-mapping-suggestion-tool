import { useId, useRef } from 'react';
import { Box, Button, Paper, Typography } from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import UploadFileIcon from '@mui/icons-material/UploadFile';

const KILOBYTE = 1024;

function sizeLabel(file) {
  return `${Math.max(1, Math.round(file.size / KILOBYTE))} KB`;
}

export default function FilePicker({ label, hint, file, onSelect, testId }) {
  const input = useRef(null);
  const id = useId();
  const action = file ? 'Change file' : 'Choose CSV';

  return (
    <Paper
      variant="outlined"
      role="group"
      aria-labelledby={`${id}-label`}
      aria-describedby={`${id}-hint`}
      sx={{
        flex: 1,
        p: 2.5,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        borderStyle: file ? 'solid' : 'dashed',
        borderColor: file ? 'primary.main' : 'divider',
        bgcolor: file ? 'rgba(29, 92, 74, 0.04)' : 'background.paper',
      }}
    >
      <Typography variant="h3" id={`${id}-label`}>
        {label}
      </Typography>
      <Typography variant="body2" color="text.secondary" id={`${id}-hint`}>
        {hint}
      </Typography>
      <Box
        sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1.5, mt: 'auto', pt: 1 }}
      >
        <Button
          variant={file ? 'outlined' : 'contained'}
          startIcon={<UploadFileIcon />}
          onClick={() => input.current.click()}
          aria-label={`${action}: ${label.toLowerCase()}`}
        >
          {action}
        </Button>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, minWidth: 0 }}>
          {file && <CheckCircleOutlineIcon fontSize="small" color="primary" aria-hidden />}
          <Typography variant="body2" className="mono" color="text.secondary" noWrap>
            {file ? `${file.name} · ${sizeLabel(file)}` : 'No file selected'}
          </Typography>
        </Box>
      </Box>
      <input
        ref={input}
        data-testid={testId}
        type="file"
        accept=".csv,.tsv,.txt"
        hidden
        onChange={(event) => {
          const [chosen] = event.target.files;
          // Reset so picking the same file again still fires a change.
          event.target.value = '';
          if (chosen) {
            onSelect(chosen);
          }
        }}
      />
    </Paper>
  );
}
