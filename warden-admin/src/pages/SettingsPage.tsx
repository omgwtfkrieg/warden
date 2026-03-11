import { Box, Paper, Typography } from '@mui/material'

export function SettingsPage() {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" fontWeight={600} gutterBottom>Settings</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>System configuration</Typography>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="body2" color="text.disabled">Settings coming in Phase E.</Typography>
      </Paper>
    </Box>
  )
}
