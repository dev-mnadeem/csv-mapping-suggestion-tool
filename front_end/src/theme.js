import { createTheme } from '@mui/material/styles';

// A ledger look for a data-import tool: warm paper, bookkeeping green, an
// ochre accent for rows that need a human to check them. Column names and
// cell values are set in a monospace face so "Policy_No" reads as data.
const INK = '#22302b';
const MUTED = '#5c6660';
const RULE = '#ddd7c8';

export const MONO = "'IBM Plex Mono', ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace";

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1d5c4a', contrastText: '#ffffff' },
    secondary: { main: '#2e6f8e', contrastText: '#ffffff' },
    success: { main: '#1d5c4a' },
    info: { main: '#2e6f8e' },
    warning: { main: '#a8611a' },
    background: { default: '#f4f1e8', paper: '#ffffff' },
    text: { primary: INK, secondary: MUTED },
    divider: RULE,
  },
  shape: { borderRadius: 6 },
  typography: {
    fontFamily: "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif",
    h1: { fontSize: '1.375rem', fontWeight: 600, letterSpacing: '-0.005em' },
    h2: { fontSize: '1.125rem', fontWeight: 600 },
    h3: { fontSize: '1rem', fontWeight: 600 },
    body2: { fontSize: '0.875rem' },
    overline: { fontFamily: MONO, fontWeight: 500, letterSpacing: '0.08em' },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: { border: `1px solid ${RULE}`, boxShadow: 'none' },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 600,
          color: MUTED,
          whiteSpace: 'nowrap',
          backgroundColor: '#faf8f2',
          borderBottomColor: RULE,
        },
        body: { borderBottomColor: '#ece7da' },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          '&.Mui-focusVisible': { outline: '3px solid #a8611a', outlineOffset: 2 },
        },
      },
    },
  },
});

export default theme;
