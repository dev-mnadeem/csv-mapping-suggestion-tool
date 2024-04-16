import React, { useRef } from 'react';
import { Box, Button, Paper, Typography } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';

const KILOBYTE = 1024;

function sizeLabel(file) {
  return `${Math.max(1, Math.round(file.size / KILOBYTE))} KB`;
}

export default function FilePicker({ label, hint, file, onSelect, testId }) {
  const input = useRef(null);

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2.5,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        borderStyle: file ? 'solid' : 'dashed',
        borderColor: file ? 'secondary.main' : 'divider',
        backgroundColor: file ? 'rgba(47, 143, 111, 0.04)' : 'background.paper',
      }}
    >
      <Typography variant="h2">{label}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ minHeight: 40 }}>
        {hint}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mt: 'auto' }}>
        <Button
          variant={file ? 'outlined' : 'contained'}
          startIcon={<UploadFileIcon />}
          onClick={() => input.current.click()}
        >
          {file ? 'Change file' : 'Choose CSV'}
        </Button>
        <Typography variant="body2" className="mono" color="text.secondary" noWrap>
          {file ? `${file.name} · ${sizeLabel(file)}` : 'No file selected'}
        </Typography>
      </Box>
      <input
        ref={input}
        data-testid={testId}
        type="file"
        accept=".csv,.tsv,.txt"
        hidden
        onChange={(event) => onSelect(event.target.files[0])}
      />
    </Paper>
  );
}
