import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Divider,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import DownloadIcon from '@mui/icons-material/Download';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import FilePicker from './components/FilePicker';
import MappingTable from './components/MappingTable';
import ResultPreview from './components/ResultPreview';
import TableFacts from './components/TableFacts';
import {
  applyMapping,
  downloadMapped,
  fetchTransforms,
  suggestMapping,
} from './api/client';

const PREVIEW_ROWS = 25;
const RESULT_FILENAME = 'mapped.csv';

function toMappings(suggestions) {
  return suggestions.map((item) => ({
    target_column: item.target_column,
    source_column: item.best ? item.best.source_column : null,
    transform: item.best ? item.best.transform : 'identity',
    options: item.best ? item.best.transform_options : {},
    confidence: item.best ? item.best.confidence : 0,
    rationale: item.best ? item.best.rationale : 'no column scored above the threshold',
  }));
}

function toPlan(mappings) {
  return mappings.map(({ target_column, source_column, transform, options }) => ({
    target_column,
    source_column,
    transform,
    options,
  }));
}

function SectionHeading({ step, title, subtitle, action }) {
  return (
    <Stack
      direction="row"
      justifyContent="space-between"
      alignItems="flex-start"
      spacing={2}
      sx={{ mb: 2 }}
    >
      <Box>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Chip label={step} size="small" color="primary" />
          <Typography variant="h2">{title}</Typography>
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
          {subtitle}
        </Typography>
      </Box>
      {action}
    </Stack>
  );
}

export default function App() {
  const [inputFile, setInputFile] = useState(null);
  const [targetFile, setTargetFile] = useState(null);
  const [transforms, setTransforms] = useState([]);
  const [suggestion, setSuggestion] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTransforms()
      .then(setTransforms)
      .catch(() => setError('The API is not reachable. Start the backend on port 7241.'));
  }, []);

  const run = useCallback(async (name, action) => {
    setBusy(name);
    setError(null);
    try {
      await action();
    } catch (problem) {
      setError(problem.message);
    } finally {
      setBusy(null);
    }
  }, []);

  const handleSuggest = () =>
    run('suggest', async () => {
      const response = await suggestMapping(inputFile, targetFile);
      setSuggestion(response);
      setMappings(toMappings(response.suggestions));
      setResult(null);
    });

  const handleApply = () =>
    run('apply', async () => {
      setResult(await applyMapping(inputFile, toPlan(mappings), PREVIEW_ROWS));
    });

  const handleDownload = () =>
    run('download', async () => {
      const blob = await downloadMapped(inputFile, toPlan(mappings));
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = RESULT_FILENAME;
      anchor.click();
      URL.revokeObjectURL(url);
    });

  const matched = mappings.filter((row) => row.source_column).length;

  return (
    <Box sx={{ minHeight: '100%', pb: 8 }}>
      <Box sx={{ bgcolor: 'primary.main', color: 'common.white', py: 4, mb: 4 }}>
        <Container maxWidth="lg">
          <Typography variant="h1">CSV Column Mapper</Typography>
          <Typography variant="body1" sx={{ opacity: 0.85, mt: 1 }}>
            Point a messy export at the schema you need and get a column-by-column
            mapping, with the reason for every choice.
          </Typography>
        </Container>
      </Box>

      <Container maxWidth="lg">
        <Stack spacing={4}>
          {error && (
            <Alert severity="error" onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Paper sx={{ p: 3 }}>
            <SectionHeading
              step="1"
              title="Upload the two files"
              subtitle="The file you have, and a file with the header row you need."
              action={
                <Button
                  variant="contained"
                  size="large"
                  startIcon={
                    busy === 'suggest' ? (
                      <CircularProgress size={18} color="inherit" />
                    ) : (
                      <AutoFixHighIcon />
                    )
                  }
                  disabled={!inputFile || !targetFile || busy === 'suggest'}
                  onClick={handleSuggest}
                >
                  Suggest mapping
                </Button>
              }
            />
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <Box sx={{ flex: 1 }}>
                <FilePicker
                  label="Source file"
                  hint="The export being mapped, for example a policy list from another system."
                  file={inputFile}
                  testId="input-file"
                  onSelect={setInputFile}
                />
              </Box>
              <Box sx={{ flex: 1 }}>
                <FilePicker
                  label="Target schema"
                  hint="A CSV whose header row is the schema you want to end up with."
                  file={targetFile}
                  testId="target-file"
                  onSelect={setTargetFile}
                />
              </Box>
            </Stack>
          </Paper>

          {suggestion && (
            <Paper sx={{ p: 3 }}>
              <SectionHeading
                step="2"
                title="Review the suggested mapping"
                subtitle={`${matched} of ${mappings.length} target columns matched by the ${suggestion.suggester} matcher in ${suggestion.duration_ms} ms. Change anything that looks wrong.`}
                action={
                  <Button
                    variant="contained"
                    size="large"
                    color="secondary"
                    startIcon={
                      busy === 'apply' ? (
                        <CircularProgress size={18} color="inherit" />
                      ) : (
                        <PlayArrowIcon />
                      )
                    }
                    disabled={busy === 'apply'}
                    onClick={handleApply}
                  >
                    Apply mapping
                  </Button>
                }
              />
              <Stack spacing={1.5} sx={{ mb: 2.5 }}>
                <TableFacts summary={suggestion.source} role="source" />
                <TableFacts summary={suggestion.target} role="target" />
              </Stack>
              {suggestion.warnings.length > 0 && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  {suggestion.warnings.join(' ')}
                </Alert>
              )}
              <Divider sx={{ mb: 2 }} />
              <MappingTable
                mappings={mappings}
                sourceColumns={suggestion.source.columns}
                transforms={transforms}
                onChange={setMappings}
              />
            </Paper>
          )}

          {result && (
            <Paper sx={{ p: 3 }}>
              <SectionHeading
                step="3"
                title="Mapped result"
                subtitle="Every value produced by the transforms you approved."
                action={
                  <Button
                    variant="outlined"
                    size="large"
                    startIcon={<DownloadIcon />}
                    disabled={busy === 'download'}
                    onClick={handleDownload}
                  >
                    Download CSV
                  </Button>
                }
              />
              {result.warnings.length > 0 && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  {result.warnings.join(' ')}
                </Alert>
              )}
              <ResultPreview result={result} />
            </Paper>
          )}
        </Stack>
      </Container>
    </Box>
  );
}
