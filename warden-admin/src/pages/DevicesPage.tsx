import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, DialogContentText,
  IconButton, Paper, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, TextField, Typography, Stack, Alert, Tooltip,
} from '@mui/material'
import AndroidIcon from '@mui/icons-material/Android'
import BlockIcon from '@mui/icons-material/Block'
import ComputerIcon from '@mui/icons-material/Computer'
import DeleteIcon from '@mui/icons-material/Delete'
import DesktopWindowsIcon from '@mui/icons-material/DesktopWindows'
import EditIcon from '@mui/icons-material/Edit'
import LaptopMacIcon from '@mui/icons-material/LaptopMac'
import PhoneIphoneIcon from '@mui/icons-material/PhoneIphone'
import RefreshIcon from '@mui/icons-material/Refresh'
import ReplayIcon from '@mui/icons-material/Replay'
import RestartAltIcon from '@mui/icons-material/RestartAlt'
import { devicesApi } from '@/api/devices'
import type { Device } from '@/api/devices'

const PLATFORM_ICONS: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  linux:   { icon: ComputerIcon,        color: '#1976d2', label: 'Linux' },
  android: { icon: AndroidIcon,         color: '#388e3c', label: 'Android' },
  ios:     { icon: PhoneIphoneIcon,     color: '#7b1fa2', label: 'iOS' },
  windows: { icon: DesktopWindowsIcon,  color: '#0288d1', label: 'Windows' },
  macos:   { icon: LaptopMacIcon,       color: '#455a64', label: 'macOS' },
}

const ONLINE_THRESHOLD_MS = 90_000 // 90s — 3 missed 30s polls

function isOnline(lastSeenAt: string | null): boolean {
  if (!lastSeenAt) return false
  return Date.now() - new Date(lastSeenAt).getTime() < ONLINE_THRESHOLD_MS
}

function PlatformIcon({ platform }: { platform: string | null }) {
  if (!platform) return null
  const p = PLATFORM_ICONS[platform]
  if (!p) return null
  const Icon = p.icon
  return (
    <Tooltip title={p.label}>
      <Icon sx={{ fontSize: 18, color: p.color }} />
    </Tooltip>
  )
}

function DeviceStatus({ lastSeenAt, revoked }: { lastSeenAt: string | null; revoked: boolean }) {
  if (revoked) return <Typography variant="caption" color="text.disabled">—</Typography>
  const online = isOnline(lastSeenAt)
  const label = online ? 'Online' : lastSeenAt ? 'Offline' : 'Never seen'
  return (
    <Stack direction="row" spacing={0.5} alignItems="center">
      <Box component="span" sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: online ? '#4caf50' : '#9e9e9e', flexShrink: 0 }} />
      <Typography variant="caption" color={online ? 'success.main' : 'text.secondary'}>{label}</Typography>
    </Stack>
  )
}

export function DevicesPage() {
  const qc = useQueryClient()
  const [activateOpen, setActivateOpen] = useState(false)
  const [code, setCode] = useState('')
  const [deviceName, setDeviceName] = useState('')
  const [activateError, setActivateError] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<Device | null>(null)
  const [renameTarget, setRenameTarget] = useState<Device | null>(null)
  const [renameValue, setRenameValue] = useState('')

  const { data: devices = [], isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: devicesApi.list,
  })

  const revokeMutation = useMutation({
    mutationFn: devicesApi.revoke,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['devices'] }),
  })

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => devicesApi.rename(id, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['devices'] })
      setRenameTarget(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => devicesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['devices'] })
      setDeleteTarget(null)
    },
  })

  const commandMutation = useMutation({
    mutationFn: ({ id, command }: { id: number; command: 'reconnect' | 'reload' | 'refresh' }) =>
      devicesApi.sendCommand(id, command),
  })

  const activateMutation = useMutation({
    mutationFn: () => devicesApi.activate(code.trim().toUpperCase(), deviceName || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['devices'] })
      setActivateOpen(false)
      setCode('')
      setDeviceName('')
      setActivateError('')
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setActivateError(err.response?.data?.detail ?? 'Activation failed')
    },
  })

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h6" fontWeight={600}>Devices</Typography>
          <Typography variant="body2" color="text.secondary">Authorized Flutter app devices</Typography>
        </Box>
        <Button variant="contained" onClick={() => setActivateOpen(true)}>Authorize Device</Button>
      </Box>

      <Dialog open={activateOpen} onClose={() => { setActivateOpen(false); setActivateError('') }} fullWidth maxWidth="xs">
        <DialogTitle>Authorize Device</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>Enter the pairing code shown on the Flutter app.</DialogContentText>
          <Stack spacing={2}>
            <TextField
              label="Pairing Code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="XXXX-XXXX"
              inputProps={{ maxLength: 9, style: { textAlign: 'center', fontFamily: 'monospace', fontSize: 20, letterSpacing: 6, textTransform: 'uppercase' } }}
              fullWidth
            />
            <TextField
              label="Device Name (optional)"
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
              placeholder="Living Room TV"
              fullWidth
            />
            {activateError && <Alert severity="error">{activateError}</Alert>}
            <Stack direction="row" spacing={1} justifyContent="flex-end">
              <Button onClick={() => { setActivateOpen(false); setActivateError('') }}>Cancel</Button>
              <Button
                variant="contained"
                onClick={() => activateMutation.mutate()}
                disabled={code.length < 9 || activateMutation.isPending}
              >
                {activateMutation.isPending ? 'Authorizing...' : 'Authorize'}
              </Button>
            </Stack>
          </Stack>
        </DialogContent>
      </Dialog>

      <TableContainer component={Paper} variant="outlined">
        {isLoading ? (
          <Typography variant="body2" color="text.disabled" sx={{ p: 3 }}>Loading...</Typography>
        ) : devices.length === 0 ? (
          <Typography variant="body2" color="text.disabled" sx={{ p: 3 }}>No devices authorized yet.</Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Device</TableCell>
                <TableCell>Paired At</TableCell>
                <TableCell>Auth Status</TableCell>
                <TableCell>Device Status</TableCell>
                <TableCell align="right"></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {devices.map((device) => (
                <TableRow key={device.id}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <PlatformIcon platform={device.platform} />
                      <Box>
                        <Typography variant="body2" fontWeight={500} color={device.device_name ? 'text.primary' : 'text.disabled'}>
                          {device.device_name ?? 'Unnamed'}
                        </Typography>
                        {device.device_model && (
                          <Typography variant="caption" color="text.disabled">
                            {device.device_model}
                          </Typography>
                        )}
                      </Box>
                      <Tooltip title="Rename">
                        <IconButton size="small" onClick={() => { setRenameTarget(device); setRenameValue(device.device_name ?? '') }}>
                          <EditIcon sx={{ fontSize: 14 }} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(device.paired_at).toLocaleString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={device.revoked ? 'Revoked' : 'Active'}
                      size="small"
                      color={device.revoked ? 'error' : 'success'}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <DeviceStatus lastSeenAt={device.last_seen_at} revoked={device.revoked} />
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                      {!device.revoked && (
                        <>
                          <Tooltip title="Reconnect streams">
                            <IconButton size="small" onClick={() => commandMutation.mutate({ id: device.id, command: 'reconnect' })}>
                              <ReplayIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Reload app">
                            <IconButton size="small" onClick={() => commandMutation.mutate({ id: device.id, command: 'reload' })}>
                              <RestartAltIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Refresh camera list">
                            <IconButton size="small" onClick={() => commandMutation.mutate({ id: device.id, command: 'refresh' })}>
                              <RefreshIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Revoke access">
                            <IconButton
                              size="small"
                              color="warning"
                              onClick={() => { if (confirm('Revoke this device?')) revokeMutation.mutate(device.id) }}
                            >
                              <BlockIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                      <Tooltip title={device.revoked ? 'Delete permanently' : 'Revoke first to delete'}>
                        <span>
                          <IconButton
                            size="small"
                            color="error"
                            disabled={!device.revoked}
                            onClick={() => setDeleteTarget(device)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <Dialog open={!!renameTarget} onClose={() => setRenameTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Rename Device</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Device Name"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && renameTarget) renameMutation.mutate({ id: renameTarget.id, name: renameValue }) }}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameTarget(null)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={renameMutation.isPending}
            onClick={() => renameTarget && renameMutation.mutate({ id: renameTarget.id, name: renameValue })}
          >
            {renameMutation.isPending ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Delete Device</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Permanently delete <strong>{deleteTarget?.device_name ?? 'this device'}</strong>
            {deleteTarget?.device_model ? ` (${deleteTarget.device_model})` : ''}? This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
