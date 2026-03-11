import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#3b82f6' },
    background: { default: '#020817', paper: '#0f172a' },
  },
  shape: { borderRadius: 8 },
  components: {
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: 'rgba(255,255,255,0.08)' },
      },
    },
  },
})
