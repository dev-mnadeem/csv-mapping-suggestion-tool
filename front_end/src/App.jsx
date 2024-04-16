import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
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
import { applyMapping, downloadMapped, fetchHealth, fetchTransforms, suggestMapping } from './api/client';

const PREVIEW_ROWS = 25;
const RESULT_FILENAME = 'mapped.csv';
const NO_MATCH = 'no column scored above the threshold';

function toMappings(suggestions) {
  return suggestions.map((item) => ({
    target_column: item.target_column,
    source_column: item.best ? item.best.source_column : null,
    transform: item.best ? item.best.transform : 'identity',
    options: item.best ? item.best.transform_options : {},
    confidence: item.best ? item.best.confidence : 0,
    rationale: item.best ? item.best.rationale : NO_MATCH,
    candidates: [item.best, ...item.alternatives].filter(Boolean),
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

function BusyIcon({ busy, icon }) {
  return busy ? <CircularProgress size={18} color="inherit" aria-hidden /> : icon;
}

function Section({ step, title, subtitle, action, children, labelId }) {
  return (
    <Paper component="section" aria-labelledby={labelId} sx={{ p: { xs: 2, sm: 3 } }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'flex-start' }}
        spacing={2}
        sx={{ mb: 2.5 }}
      >
        <Box>
          <Typography variant="overline" color="primary" component="p">
            Step {step}
          </Typography>
          <Typography variant="h2" id={labelId}>
            {title}
          </Typography>
          {subtitle && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }} role="status">
              {subtitle}
            </Typography>
          )}
        </Box>
        {action}
      </Stack>
      {children}
    </Paper>
  );
}

function ApiStatus({ health }) {
  if (health === undefined) {
    return <Chip size="small" variant="outlined" label="checking API…" />;
  }
  if (health === null) {
    return <Chip size="small" color="warning" label="API offline" />;
  }
  const label = `${health.suggester} matcher · v${health.version}`;
  return <Chip size="small" variant="outlined" color="primary" label={label} className="mono" />;
}

export default function App() {
  const [inputFile, setInputFile] = useState(null);
  const [targetFile, setTargetFile] = useState(null);
  const [health, setHealth] = useState(undefined);
  const [transforms, setTransforms] = useState([]);
  const [suggestion, setSuggestion] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([fetchHealth(), fetchTransforms()])
      .then(([status, catalogue]) => {
        setHealth(status);
        setTransforms(catalogue);
      })
      .catch(() => {
        setHealth(null);
        setError('The API is not reachable. Start the backend on port 7241.');
      });
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

  const chooseFile = (setFile) => (file) => {
    setFile(file);
    // A plan only fits the file it was suggested for.
    setSuggestion(null);
    setMappings([]);
    setResult(null);
  };

  const editMappings = (next) => {
    setMappings(next);
    setResult(null);
  };

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
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      // Revoking synchronously can cancel the download before it starts.
      setTimeout(() => URL.revokeObjectURL(url), 0);
    });

  const matched = mappings.filter((row) => row.source_column).length;
  const bothChosen = Boolean(inputFile && targetFile);

  return (
    <Box sx={{ minHeight: '100vh', pb: 8 }}>
      <Box
        component="header"
        sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper', mb: { xs: 2, sm: 4 } }}
      >
        <Container
          maxWidth="lg"
          sx={{
            py: 2,
            display: 'flex',
            flexWrap: 'wrap',
            gap: 1.5,
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Box>
            <Typography variant="h1">CSV Column Mapper</Typography>
            <Typography variant="body2" color="text.secondary">
              Match an export&apos;s columns to the schema you need, check each pairing, then download.
            </Typography>
          </Box>
          <ApiStatus health={health} />
        </Container>
      </Box>

      <Container maxWidth="lg" component="main">
        <Stack spacing={{ xs: 2, sm: 3 }}>
          {error && (
            <Alert severity="error" onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Section
            step="1"
            labelId="step-upload"
            title="Upload the two files"
            subtitle="The file you have, and a file whose header row is the schema you need."
            action={
              <Button
                variant="contained"
                size="large"
                startIcon={<BusyIcon busy={busy === 'suggest'} icon={<AutoFixHighIcon />} />}
                disabled={!bothChosen || busy === 'suggest'}
                onClick={handleSuggest}
              >
                Suggest mapping
              </Button>
            }
          >
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <FilePicker
                label="Source file"
                hint="The export being mapped, for example a policy list from another system."
                file={inputFile}
                testId="input-file"
                onSelect={chooseFile(setInputFile)}
              />
              <FilePicker
                label="Target schema"
                hint="A CSV whose header row lists the columns you want to end up with."
                file={targetFile}
                testId="target-file"
                onSelect={chooseFile(setTargetFile)}
              />
            </Stack>
          </Section>

          {suggestion ? (
            <Section
              step="2"
              labelId="step-review"
              title="Review the suggested mapping"
              subtitle={`${matched} of ${mappings.length} target columns matched by the ${suggestion.suggester} matcher in ${suggestion.duration_ms} ms. Change anything that looks wrong.`}
              action={
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<BusyIcon busy={busy === 'apply'} icon={<PlayArrowIcon />} />}
                  disabled={busy === 'apply'}
                  onClick={handleApply}
                >
                  Apply mapping
                </Button>
              }
            >
              <Stack spacing={1} sx={{ mb: 2 }}>
                <TableFacts summary={suggestion.source} role="source" />
                <TableFacts summary={suggestion.target} role="target" />
              </Stack>
              {suggestion.warnings.length > 0 && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  {suggestion.warnings.join(' ')}
                </Alert>
              )}
              <MappingTable
                mappings={mappings}
                sourceColumns={suggestion.source.columns}
                transforms={transforms}
                onChange={editMappings}
              />
            </Section>
          ) : (
            <Paper
              component="section"
              aria-label="Mapping review"
              sx={{ p: { xs: 2, sm: 3 }, borderStyle: 'dashed', bgcolor: 'transparent' }}
            >
              <Typography variant="overline" color="text.secondary" component="p">
                Step 2
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {bothChosen
                  ? 'Both files are ready. Press Suggest mapping to see a source column, transform and confidence for every target column.'
                  : 'Choose both files and the suggested mapping appears here, one row per target column, each with the reason it was picked.'}
              </Typography>
            </Paper>
          )}

          {result && (
            <Section
              step="3"
              labelId="step-result"
              title="Mapped result"
              subtitle="Every value produced by the transforms you approved."
              action={
                <Button
                  variant="outlined"
                  size="large"
                  startIcon={<BusyIcon busy={busy === 'download'} icon={<DownloadIcon />} />}
                  disabled={busy === 'download'}
                  onClick={handleDownload}
                >
                  Download CSV
                </Button>
              }
            >
              {result.warnings.length > 0 && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  {result.warnings.join(' ')}
                </Alert>
              )}
              <ResultPreview result={result} />
            </Section>
          )}
        </Stack>
      </Container>
    </Box>
  );
}
