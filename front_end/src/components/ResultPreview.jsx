import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';

export default function ResultPreview({ result }) {
  return (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }} id="result-caption">
        Showing {result.rows.length} of {result.total_rows} mapped rows.
      </Typography>
      <TableContainer
        component={Paper}
        variant="outlined"
        sx={{ maxHeight: 360 }}
        tabIndex={0}
        aria-labelledby="result-caption"
      >
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {result.columns.map((column) => (
                <TableCell key={column} className="mono">
                  {column}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {result.rows.map((row, index) => (
              <TableRow key={index} hover>
                {result.columns.map((column) => (
                  <TableCell key={column} className="mono" sx={{ whiteSpace: 'nowrap' }}>
                    {row[column]}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}
