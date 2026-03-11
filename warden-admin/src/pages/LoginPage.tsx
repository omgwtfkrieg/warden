import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Button, Paper, TextField, Typography, Alert } from '@mui/material'
import { useAuth } from '@/hooks/useAuth'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, loading, error } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const ok = await login(email, password)
    if (ok) navigate('/')
  }

  return (
    <Box
      sx={{
        display: 'flex',
        minHeight: '100vh',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
      }}
    >
      <Paper
        elevation={3}
        sx={{ width: '100%', maxWidth: 380, p: 4 }}
        component="form"
        onSubmit={handleSubmit}
      >
        <Box sx={{ mb: 3, textAlign: 'center' }}>
          <Box component="img" src="/logo.svg" alt="Warden" sx={{ height: 64, mb: 2 }} />
          <Typography variant="body2" color="text.secondary">Sign in to the admin panel</Typography>
        </Box>

        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="admin@warden.local"
          required
          fullWidth
          sx={{ mb: 2 }}
        />

        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          fullWidth
          sx={{ mb: 2 }}
        />

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Button type="submit" variant="contained" fullWidth disabled={loading}>
          {loading ? 'Signing in...' : 'Sign in'}
        </Button>
      </Paper>
    </Box>
  )
}
