import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, DialogContentText,
  IconButton, Paper, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, TextField, Typography, Stack, Alert, Tooltip,
} from '@mui/material'
import BlockIcon from '@mui/icons-material/Block'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import { devicesApi } from '@/api/devices'
import type { Device } from '@/api/devices'

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
                <TableCell>Device Name</TableCell>
                <TableCell>Paired At</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right"></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {devices.map((device) => (
                <TableRow key={device.id}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
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
                  <TableCell align="right">
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                      {!device.revoked && (
                        <Tooltip title="Revoke access">
                          <IconButton
                            size="small"
                            color="warning"
                            onClick={() => { if (confirm('Revoke this device?')) revokeMutation.mutate(device.id) }}
                          >
                            <BlockIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
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
