import React from 'react';
import {
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import Confidence from './Confidence';

export const UNMAPPED = '__none__';

// Every row is editable: the suggestion is a starting point, and the
// person doing the import has the final say before anything runs.
export default function MappingTable({
  mappings,
  sourceColumns,
  transforms,
  onChange,
}) {
  const update = (targetColumn, patch) =>
    onChange(
      mappings.map((row) =>
        row.target_column === targetColumn ? { ...row, ...patch } : row
      )
    );

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Target column</TableCell>
            <TableCell>Source column</TableCell>
            <TableCell>Transform</TableCell>
            <TableCell>Confidence</TableCell>
            <TableCell>Why</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {mappings.map((row) => (
            <TableRow key={row.target_column} hover>
              <TableCell>
                <Typography variant="body2" fontWeight={650} className="mono">
                  {row.target_column}
                </Typography>
              </TableCell>
              <TableCell>
                <Select
                  size="small"
                  fullWidth
                  className="mono"
                  value={row.source_column || UNMAPPED}
                  inputProps={{ 'aria-label': `source for ${row.target_column}` }}
                  onChange={(event) =>
                    update(row.target_column, {
                      source_column:
                        event.target.value === UNMAPPED ? null : event.target.value,
                    })
                  }
                >
                  <MenuItem value={UNMAPPED}>
                    <em>leave blank</em>
                  </MenuItem>
                  {sourceColumns.map((column) => (
                    <MenuItem key={column.name} value={column.name}>
                      {column.name}
                    </MenuItem>
                  ))}
                </Select>
              </TableCell>
              <TableCell>
                <Select
                  size="small"
                  fullWidth
                  value={row.transform}
                  inputProps={{ 'aria-label': `transform for ${row.target_column}` }}
                  onChange={(event) =>
                    update(row.target_column, { transform: event.target.value })
                  }
                >
                  {transforms.map((transform) => (
                    <MenuItem key={transform.name} value={transform.name}>
                      {transform.name}
                    </MenuItem>
                  ))}
                </Select>
              </TableCell>
              <TableCell>
                <Confidence value={row.confidence} rationale={row.rationale} />
              </TableCell>
              <TableCell sx={{ maxWidth: 300 }}>
                <Typography variant="body2" color="text.secondary">
                  {row.rationale}
                </Typography>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
