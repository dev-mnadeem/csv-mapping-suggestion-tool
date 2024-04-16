import {
  Box,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import Confidence from './Confidence';

export const UNMAPPED = '__none__';

// Picking a different source swaps in that pairing's own score, reason and
// transform when the matcher scored it, instead of keeping the old ones.
export function withSource(row, sourceColumn) {
  if (sourceColumn === null) {
    return {
      ...row,
      source_column: null,
      transform: 'identity',
      options: {},
      confidence: 0,
      rationale: 'left blank',
    };
  }
  const scored = row.candidates.find((candidate) => candidate.source_column === sourceColumn);
  if (scored) {
    return {
      ...row,
      source_column: sourceColumn,
      transform: scored.transform,
      options: scored.transform_options,
      confidence: scored.confidence,
      rationale: scored.rationale,
    };
  }
  return {
    ...row,
    source_column: sourceColumn,
    transform: 'identity',
    options: {},
    confidence: null,
    rationale: 'chosen by hand',
  };
}

// Options belong to one transform, so they are dropped on a switch, except
// when switching back to the transform the matcher proposed for this source.
export function withTransform(row, transform) {
  const scored = row.candidates.find((candidate) => candidate.source_column === row.source_column);
  const options = scored && scored.transform === transform ? scored.transform_options : {};
  return { ...row, transform, options };
}

function SourceSelect({ row, sourceColumns, onPick }) {
  return (
    <Select
      size="small"
      fullWidth
      className="mono"
      value={row.source_column || UNMAPPED}
      slotProps={{ input: { 'aria-label': `source for ${row.target_column}` } }}
      onChange={(event) => onPick(event.target.value === UNMAPPED ? null : event.target.value)}
    >
      <MenuItem value={UNMAPPED}>
        <em>leave blank</em>
      </MenuItem>
      {sourceColumns.map((column) => (
        <MenuItem key={column.name} value={column.name} className="mono">
          {column.name}
        </MenuItem>
      ))}
    </Select>
  );
}

function TransformSelect({ row, transforms, onPick }) {
  // Until the catalogue loads, offer the current value so the select is never empty.
  const names = transforms.length ? transforms.map((item) => item.name) : [row.transform];
  return (
    <Select
      size="small"
      fullWidth
      className="mono"
      value={row.transform}
      slotProps={{ input: { 'aria-label': `transform for ${row.target_column}` } }}
      onChange={(event) => onPick(event.target.value)}
    >
      {names.map((name) => (
        <MenuItem key={name} value={name} className="mono">
          {name}
        </MenuItem>
      ))}
    </Select>
  );
}

function StackedRows({ mappings, renderSource, renderTransform }) {
  return (
    <Stack component="ul" spacing={1.5} sx={{ listStyle: 'none', p: 0, m: 0 }}>
      {mappings.map((row) => (
        <Paper component="li" variant="outlined" key={row.target_column} sx={{ p: 2 }}>
          <Typography variant="overline" color="text.secondary" component="p">
            Target column
          </Typography>
          <Typography variant="h3" className="mono" sx={{ mb: 1.5 }}>
            {row.target_column}
          </Typography>
          <Stack spacing={1.25}>
            {renderSource(row)}
            {renderTransform(row)}
            <Confidence value={row.confidence} />
            <Typography variant="body2" color="text.secondary">
              {row.rationale}
            </Typography>
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}

// Every row is editable: the suggestion is a starting point, and the
// person doing the import has the final say before anything runs.
export default function MappingTable({ mappings, sourceColumns, transforms, onChange }) {
  const theme = useTheme();
  const narrow = useMediaQuery(theme.breakpoints.down('md'));

  const update = (targetColumn, change) =>
    onChange(mappings.map((row) => (row.target_column === targetColumn ? change(row) : row)));

  const renderSource = (row) => (
    <SourceSelect
      row={row}
      sourceColumns={sourceColumns}
      onPick={(source) => update(row.target_column, (current) => withSource(current, source))}
    />
  );
  const renderTransform = (row) => (
    <TransformSelect
      row={row}
      transforms={transforms}
      onPick={(name) => update(row.target_column, (current) => withTransform(current, name))}
    />
  );

  if (narrow) {
    return (
      <StackedRows
        mappings={mappings}
        renderSource={renderSource}
        renderTransform={renderTransform}
      />
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small" aria-label="Suggested column mapping">
        <TableHead>
          <TableRow>
            <TableCell>Target column</TableCell>
            <TableCell sx={{ width: '22%' }}>Source column</TableCell>
            <TableCell sx={{ width: '18%' }}>Transform</TableCell>
            <TableCell>Confidence</TableCell>
            <TableCell>Why</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {mappings.map((row) => (
            <TableRow key={row.target_column} hover>
              <TableCell component="th" scope="row">
                <Typography variant="body2" className="mono" sx={{ fontWeight: 600 }}>
                  {row.target_column}
                </Typography>
              </TableCell>
              <TableCell>{renderSource(row)}</TableCell>
              <TableCell>{renderTransform(row)}</TableCell>
              <TableCell>
                <Confidence value={row.confidence} />
              </TableCell>
              <TableCell sx={{ maxWidth: 300 }}>
                <Box component="span" sx={{ typography: 'body2', color: 'text.secondary' }}>
                  {row.rationale}
                </Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
