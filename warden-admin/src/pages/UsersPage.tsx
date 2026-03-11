import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Alert, Box, Button, Chip, CircularProgress, Dialog, DialogContent,
  DialogTitle, DialogContentText, Divider, FormControl, IconButton,
  InputLabel, MenuItem, Paper, Select, Stack, Switch, FormControlLabel,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  TextField, Tooltip, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import LockResetIcon from '@mui/icons-material/LockReset'
import { usersApi, type User, type Role } from '@/api/users'

// ---------------------------------------------------------------------------
// Role chip colour
// ---------------------------------------------------------------------------

function roleColor(name: string): 'error' | 'warning' | 'default' {
  if (name === 'admin') return 'error'
  if (name === 'operator') return 'warning'
  return 'default'
}

// ---------------------------------------------------------------------------
// User Form (create / edit)
// ---------------------------------------------------------------------------

function UserForm({
  initial,
  roles,
  onSubmit,
  onCancel,
  loading,
  isEdit,
}: {
  initial?: Partial<{ email: string; role_id: number; is_active: boolean }>
  roles: Role[]
  onSubmit: (data: Record<string, unknown>) => void
  onCancel: () => void
  loading: boolean
  isEdit: boolean
}) {
  const [email, setEmail] = useState(initial?.email ?? '')
  const [password, setPassword] = useState('')
  const [roleId, setRoleId] = useState<number>(initial?.role_id ?? (roles[0]?.id ?? 0))
  const [isActive, setIsActive] = useState(initial?.is_active ?? true)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (isEdit) {
      onSubmit({ email: email || undefined, role_id: roleId, is_active: isActive })
    } else {
      onSubmit({ email, password, role_id: roleId })
    }
  }

  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Stack spacing={2.5} sx={{ mt: 1 }}>
        <TextField
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required={!isEdit}
          fullWidth
          placeholder="user@example.com"
        />

        {!isEdit && (
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            fullWidth
            placeholder="••••••••"
          />
        )}

        <FormControl fullWidth>
          <InputLabel>Role</InputLabel>
          <Select
            value={roleId}
            label="Role"
            onChange={(e) => setRoleId(Number(e.target.value))}
          >
            {roles.map((r) => (
              <MenuItem key={r.id} value={r.id}>{r.name}</MenuItem>
            ))}
          </Select>
        </FormControl>

        {isEdit && (
          <FormControlLabel
            control={<Switch checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />}
            label={
              <Box>
                <Typography variant="body2">Account active</Typography>
                <Typography variant="caption" color="text.secondary">
                  Inactive users cannot log in
                </Typography>
              </Box>
            }
          />
        )}

        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button onClick={onCancel}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={loading}>
            {loading ? 'Saving...' : isEdit ? 'Save Changes' : 'Create User'}
          </Button>
        </Stack>
      </Stack>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Reset Password Dialog
// ---------------------------------------------------------------------------

function ResetPasswordDialog({
  user,
  onClose,
}: {
  user: User
  onClose: () => void
}) {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 6) { setError('Password must be at least 6 characters'); return }
    setError('')
    setSaving(true)
    try {
      await usersApi.resetPassword(user.id, password)
      onClose()
    } catch {
      setError('Failed to reset password')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Reset Password</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          Set a new password for <strong>{user.email}</strong>
        </DialogContentText>
        <Box component="form" onSubmit={handleSubmit}>
          <Stack spacing={2}>
            {error && <Alert severity="error" sx={{ py: 0 }}>{error}</Alert>}
            <TextField
              label="New Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              fullWidth
              autoFocus
            />
            <TextField
              label="Confirm Password"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              fullWidth
            />
            <Stack direction="row" spacing={1} justifyContent="flex-end">
              <Button onClick={onClose}>Cancel</Button>
              <Button type="submit" variant="contained" disabled={saving}>
                {saving ? 'Saving...' : 'Reset Password'}
              </Button>
            </Stack>
          </Stack>
        </Box>
      </DialogContent>
    </Dialog>
  )
}

// ---------------------------------------------------------------------------
// Users Page
// ---------------------------------------------------------------------------

export function UsersPage() {
  const qc = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)
  const [resetting, setResetting] = useState<User | null>(null)

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })

  const { data: roles = [] } = useQuery({
    queryKey: ['roles'],
    queryFn: usersApi.roles,
  })

  const createMutation = useMutation({
    mutationFn: (data: Parameters<typeof usersApi.create>[0]) => usersApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setCreateOpen(false) },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof usersApi.update>[1] }) =>
      usersApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setEditing(null) },
  })

  const deleteMutation = useMutation({
    mutationFn: usersApi.remove,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h6" fontWeight={600}>Users</Typography>
          <Typography variant="body2" color="text.secondary">Manage admin panel accounts and roles</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
          Add User
        </Button>
      </Box>

      {/* Create dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add User</DialogTitle>
        <DialogContent>
          <UserForm
            roles={roles}
            onSubmit={(data) => createMutation.mutate(data as Parameters<typeof usersApi.create>[0])}
            onCancel={() => setCreateOpen(false)}
            loading={createMutation.isPending}
            isEdit={false}
          />
          {createMutation.isError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {(createMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to create user'}
            </Alert>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={!!editing} onClose={() => setEditing(null)} fullWidth maxWidth="sm">
        <DialogTitle>Edit User</DialogTitle>
        <DialogContent>
          {editing && (
            <UserForm
              initial={{ email: editing.email, role_id: editing.role.id, is_active: editing.is_active }}
              roles={roles}
              onSubmit={(data) => updateMutation.mutate({ id: editing.id, data })}
              onCancel={() => setEditing(null)}
              loading={updateMutation.isPending}
              isEdit
            />
          )}
          {updateMutation.isError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {(updateMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to update user'}
            </Alert>
          )}
        </DialogContent>
      </Dialog>

      {/* Reset password dialog */}
      {resetting && (
        <ResetPasswordDialog user={resetting} onClose={() => setResetting(null)} />
      )}

      <TableContainer component={Paper} variant="outlined">
        {isLoading ? (
          <Box sx={{ p: 3, display: 'flex', gap: 1, alignItems: 'center' }}>
            <CircularProgress size={16} />
            <Typography variant="body2" color="text.disabled">Loading...</Typography>
          </Box>
        ) : users.length === 0 ? (
          <Typography variant="body2" color="text.disabled" sx={{ p: 3 }}>No users found.</Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <Typography variant="body2">{user.email}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={user.role.name}
                      size="small"
                      color={roleColor(user.role.name)}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={user.is_active ? 'Active' : 'Inactive'}
                      size="small"
                      color={user.is_active ? 'success' : 'default'}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(user.created_at).toLocaleDateString()}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Reset password">
                      <IconButton size="small" onClick={() => setResetting(user)}>
                        <LockResetIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <IconButton size="small" onClick={() => setEditing(user)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => { if (confirm(`Delete "${user.email}"?`)) deleteMutation.mutate(user.id) }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <Box sx={{ mt: 3 }}>
        <Divider sx={{ mb: 2 }} />
        <Typography variant="subtitle2" gutterBottom>Role Permissions</Typography>
        <Stack spacing={1}>
          {roles.map((role) => (
            <Box key={role.id} sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Chip label={role.name} size="small" color={roleColor(role.name)} variant="outlined" sx={{ minWidth: 80 }} />
              {role.permissions.map((p) => (
                <Chip key={p} label={p} size="small" variant="outlined" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }} />
              ))}
            </Box>
          ))}
        </Stack>
      </Box>
    </Box>
  )
}
