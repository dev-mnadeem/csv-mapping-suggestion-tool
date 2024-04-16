import { createTheme } from '@mui/material/styles';

// One place for the palette and type scale so components never hard-code
// a colour.
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1f3b63' },
    secondary: { main: '#2f8f6f' },
    background: { default: '#f4f6f9', paper: '#ffffff' },
    text: { primary: '#182634', secondary: '#5b6b7c' },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily:
      "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    h1: { fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.01em' },
    h2: { fontSize: '1.125rem', fontWeight: 650 },
    body2: { fontSize: '0.875rem' },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: { border: '1px solid #e2e8f0', boxShadow: 'none' },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: { fontWeight: 650, color: '#5b6b7c', whiteSpace: 'nowrap' },
      },
    },
  },
});

export default theme;
