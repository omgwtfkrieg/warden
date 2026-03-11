import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Alert, Box, Button, Chip, CircularProgress, Collapse, Dialog, DialogContent,
  DialogTitle, DialogContentText, Divider, FormControlLabel, IconButton,
  InputAdornment, Paper, Stack, Switch, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TextField, Tooltip, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import SearchIcon from '@mui/icons-material/Search'
import RadarIcon from '@mui/icons-material/Radar'
import WifiIcon from '@mui/icons-material/Wifi'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff'
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward'
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward'
import { camerasApi, type Camera, type CameraPayload, type StreamInfo, type StreamMetadata, type TestResult } from '@/api/cameras'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function streamLabel(s?: StreamInfo | null): string {
  if (!s) return '—'
  const parts: string[] = []
  if (s.width && s.height) parts.push(`${s.width}×${s.height}`)
  if (s.codec) parts.push(s.codec.toUpperCase())
  if (s.fps) parts.push(`${s.fps}fps`)
  if (s.bitrate_kbps) parts.push(`${s.bitrate_kbps}kbps`)
  return parts.join(' · ') || '—'
}

/** Replace the password portion of an RTSP URL with *** for display. */
function maskRtspUrl(url: string): string {
  if (!url) return url
  const withoutProto = url.replace(/^rtsp:\/\//i, '')
  const lastAt = withoutProto.lastIndexOf('@')
  if (lastAt === -1) return url
  const userinfo = withoutProto.substring(0, lastAt)
  const afterAt = withoutProto.substring(lastAt) // includes @
  const colonIdx = userinfo.indexOf(':')
  if (colonIdx === -1) return url
  const username = userinfo.substring(0, colonIdx)
  return `rtsp://${username}:***${afterAt}`
}

/** Parse IP, username, password from an RTSP URL (handles passwords containing @). */
function parseRtspUrl(url: string): { ip: string; username: string; password: string } | null {
  try {
    const withoutProto = url.replace(/^rtsp:\/\//i, '')
    const lastAt = withoutProto.lastIndexOf('@')
    if (lastAt === -1) return null
    const userinfo = withoutProto.substring(0, lastAt)
    const afterAt = withoutProto.substring(lastAt + 1)
    const colonIdx = userinfo.indexOf(':')
    if (colonIdx === -1) return null
    const username = userinfo.substring(0, colonIdx)
    const password = userinfo.substring(colonIdx + 1)
    const ipMatch = afterAt.match(/^([^:/]+)/)
    if (!ipMatch) return null
    return { ip: ipMatch[1], username, password }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Masked RTSP URL field
// ---------------------------------------------------------------------------

function RtspUrlField({
  label,
  value,
  onChange,
  placeholder,
  helperText,
  required,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  helperText?: string
  required?: boolean
}) {
  const [revealed, setRevealed] = useState(false)

  return (
    <TextField
      label={label}
      value={revealed ? value : maskRtspUrl(value)}
      onChange={(e) => { if (revealed) onChange(e.target.value) }}
      onFocus={() => setRevealed(true)}
      onBlur={() => setRevealed(false)}
      placeholder={revealed || !value ? placeholder : undefined}
      helperText={helperText}
      required={required}
      fullWidth
      slotProps={{
        input: {
          endAdornment: value ? (
            <InputAdornment position="end">
              <Tooltip title={revealed ? 'Hide credentials' : 'Reveal credentials'}>
                <IconButton size="small" onMouseDown={(e) => { e.preventDefault(); setRevealed(!revealed) }}>
                  {revealed ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
            </InputAdornment>
          ) : undefined,
        },
      }}
    />
  )
}

// ---------------------------------------------------------------------------
// Stream metadata read-only panel
// ---------------------------------------------------------------------------

function StreamMetaPanel({ label, info }: { label: string; info?: StreamInfo | null }) {
  if (!info) return null
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        {label}
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap">
        {info.width && info.height && (
          <Chip label={`${info.width}×${info.height}`} size="small" variant="outlined" />
        )}
        {info.codec && (
          <Chip label={info.codec.toUpperCase()} size="small" variant="outlined" color="primary" />
        )}
        {info.fps != null && (
          <Chip label={`${info.fps} fps`} size="small" variant="outlined" />
        )}
        {info.bitrate_kbps != null && (
          <Chip label={`${info.bitrate_kbps} kbps`} size="small" variant="outlined" />
        )}
      </Stack>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Camera Form
// ---------------------------------------------------------------------------

function CameraForm({
  initial,
  onSubmit,
  onCancel,
  loading,
}: {
  initial?: Partial<CameraPayload>
  onSubmit: (data: CameraPayload) => void
  onCancel: () => void
  loading: boolean
}) {
  const initParsed = initial?.rtsp_url ? parseRtspUrl(initial.rtsp_url) : null

  const [name, setName] = useState(initial?.name ?? '')
  const [ip, setIp] = useState(initParsed?.ip ?? '')
  const [username, setUsername] = useState(initParsed?.username ?? '')
  const [password, setPassword] = useState(initParsed?.password ?? '')
  const [mainRtsp, setMainRtsp] = useState(initial?.rtsp_url ?? '')
  const [subRtsp, setSubRtsp] = useState(initial?.sub_rtsp_url ?? '')
  const [useFfmpeg, setUseFfmpeg] = useState(initial?.use_ffmpeg ?? false)
  const [useSubStream, setUseSubStream] = useState(initial?.use_sub_stream ?? true)
  const [alwaysOn, setAlwaysOn] = useState(initial?.always_on ?? false)
  const [probedMetadata, setProbedMetadata] = useState<StreamMetadata | null>(
    (initial?.stream_metadata as StreamMetadata) ?? null
  )

  const [discovering, setDiscovering] = useState(false)
  const [discoverError, setDiscoverError] = useState('')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)

  /** When a full RTSP URL is pasted, parse credentials and IP out of it. */
  function handleMainRtspChange(url: string) {
    setMainRtsp(url)
    setTestResult(null)
    const parsed = parseRtspUrl(url)
    if (parsed) {
      setIp(parsed.ip)
      setUsername(parsed.username)
      setPassword(parsed.password)
    }
  }

  async function handleDiscover() {
    if (!ip || !username || !password) return
    setDiscovering(true)
    setDiscoverError('')
    setProbedMetadata(null)
    try {
      const result = await camerasApi.discover(ip, username, password)
      setMainRtsp(result.main_rtsp_url)
      setSubRtsp(result.sub_rtsp_url ?? '')

      if (result.metadata) {
        // Reolink API already returned full metadata
        setProbedMetadata(result.metadata)
      } else {
        // Non-Reolink: ffprobe the main RTSP URL to get stream info
        try {
          const probed = await camerasApi.probeUrl(result.main_rtsp_url)
          if (probed.metadata) setProbedMetadata(probed.metadata)
        } catch {
          // ffprobe unavailable or stream unreachable — not fatal
        }
      }
    } catch {
      setDiscoverError('Could not reach camera — check IP and credentials')
    } finally {
      setDiscovering(false)
    }
  }

  async function handleTestMain() {
    if (!mainRtsp) return
    setTesting(true)
    setTestResult(null)
    try {
      const result = await camerasApi.test(mainRtsp)
      setTestResult(result)
    } catch {
      setTestResult({ reachable: false, message: 'Request failed', video_codec: null, audio_codec: null })
    } finally {
      setTesting(false)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit({
      name,
      ip_address: ip || undefined,
      rtsp_url: mainRtsp,
      sub_rtsp_url: subRtsp || undefined,
      use_ffmpeg: useFfmpeg,
      use_sub_stream: useSubStream,
      always_on: alwaysOn,
      stream_metadata: probedMetadata ?? undefined,
    })
  }

  const canDiscover = ip.trim() && username.trim() && password.trim()
  const isDiscovered = !!probedMetadata || !!mainRtsp

  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Stack spacing={2.5} sx={{ mt: 1 }}>

        <TextField
          label="Camera Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Front Door"
          required
          fullWidth
        />

        <Divider>
          <Typography variant="caption" color="text.secondary">Camera Credentials</Typography>
        </Divider>

        <Stack direction="row" spacing={1.5}>
          <TextField
            label="IP Address"
            value={ip}
            onChange={(e) => setIp(e.target.value)}
            placeholder="192.168.1.100"
            sx={{ flex: 1 }}
          />
          <TextField
            label="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="admin"
            sx={{ flex: 1 }}
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            sx={{ flex: 1 }}
          />
        </Stack>

        <Box>
          <Button
            variant="outlined"
            startIcon={discovering ? <CircularProgress size={14} /> : <SearchIcon />}
            onClick={handleDiscover}
            disabled={!canDiscover || discovering}
            size="small"
          >
            {discovering ? 'Discovering...' : 'Discover Streams'}
          </Button>

          <Collapse in={!!discoverError}>
            <Alert severity="error" sx={{ mt: 1, py: 0 }}>{discoverError}</Alert>
          </Collapse>

          <Collapse in={isDiscovered && !discoverError}>
            <Box sx={{ mt: 1.5 }}>
              {probedMetadata && (
                <Stack spacing={1}>
                  <StreamMetaPanel label="Main Stream" info={probedMetadata.main} />
                  {probedMetadata.sub && (
                    <StreamMetaPanel label="Sub Stream" info={probedMetadata.sub} />
                  )}
                  <Typography variant="caption" color="text.secondary">
                    Source: {probedMetadata.source === 'reolink_api' ? 'Reolink API' : 'ffprobe'}
                  </Typography>
                </Stack>
              )}
            </Box>
          </Collapse>
        </Box>

        <Divider>
          <Typography variant="caption" color="text.secondary">Stream URLs</Typography>
        </Divider>

        <Box>
          <RtspUrlField
            label="Main Stream RTSP URL"
            value={mainRtsp}
            onChange={handleMainRtspChange}
            placeholder="rtsp://user:pass@192.168.1.100:554/h265Preview_01_main"
            helperText="Click to reveal · Paste a full RTSP URL to auto-fill credentials above"
            required
          />
          <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button
              size="small"
              variant="outlined"
              startIcon={testing ? <CircularProgress size={14} /> : <WifiIcon fontSize="small" />}
              onClick={handleTestMain}
              disabled={!mainRtsp || testing}
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </Button>
            {testResult && (
              <Alert severity={testResult.reachable ? 'success' : 'error'} sx={{ py: 0, flex: 1 }}>
                {testResult.reachable
                  ? `${testResult.message}${testResult.video_codec ? ` · ${testResult.video_codec}` : ''}${testResult.audio_codec ? ` · ${testResult.audio_codec}` : ''}`
                  : testResult.message}
              </Alert>
            )}
          </Box>
        </Box>

        <RtspUrlField
          label="Sub Stream RTSP URL (optional)"
          value={subRtsp}
          onChange={setSubRtsp}
          placeholder="rtsp://user:pass@192.168.1.100:554/h264Preview_01_sub"
          helperText="Lower-resolution stream for mobile / bandwidth-limited clients · Click to reveal"
        />

        <FormControlLabel
          control={<Switch checked={useFfmpeg} onChange={(e) => setUseFfmpeg(e.target.checked)} />}
          label={
            <Box>
              <Typography variant="body2">Use FFmpeg transcoding</Typography>
              <Typography variant="caption" color="text.secondary">
                Required for H.265/HEVC streams on devices without native codec support
              </Typography>
            </Box>
          }
        />

        {subRtsp && (
          <FormControlLabel
            control={<Switch checked={useSubStream} onChange={(e) => setUseSubStream(e.target.checked)} />}
            label={
              <Box>
                <Typography variant="body2">Use sub-stream for playback</Typography>
                <Typography variant="caption" color="text.secondary">
                  Stream native H.264 sub-stream instead of transcoding the main stream — smoother playback, lower resolution
                </Typography>
              </Box>
            }
          />
        )}

        <FormControlLabel
          control={<Switch checked={alwaysOn} onChange={(e) => setAlwaysOn(e.target.checked)} />}
          label={
            <Box>
              <Typography variant="body2">Keep stream warm</Typography>
              <Typography variant="caption" color="text.secondary">
                Maintains a persistent connection so the stream starts instantly (uses CPU continuously)
              </Typography>
            </Box>
          }
        />

        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button onClick={onCancel}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={loading || !mainRtsp}>
            {loading ? 'Saving...' : 'Save'}
          </Button>
        </Stack>
      </Stack>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Cameras Page
// ---------------------------------------------------------------------------

export function CamerasPage() {
  const qc = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Camera | null>(null)
  const [probingId, setProbingId] = useState<number | null>(null)

  const { data: cameras = [], isLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
  })

  const createMutation = useMutation({
    mutationFn: camerasApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['cameras'] }); setDialogOpen(false) },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CameraPayload> }) => camerasApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['cameras'] }); setEditing(null) },
  })

  const deleteMutation = useMutation({
    mutationFn: camerasApi.remove,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cameras'] }),
  })

  const reorderMutation = useMutation({
    mutationFn: camerasApi.reorder,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cameras'] }),
  })

  function handleMove(index: number, direction: 'up' | 'down') {
    const sorted = [...cameras].sort((a, b) => a.display_order - b.display_order || a.id - b.id)
    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= sorted.length) return
    // Swap positions then reassign sequential display_order values
    const reordered = [...sorted]
    ;[reordered[index], reordered[targetIndex]] = [reordered[targetIndex], reordered[index]]
    reorderMutation.mutate(reordered.map((cam, i) => ({ id: cam.id, display_order: i })))
  }

  async function handleProbe(id: number) {
    setProbingId(id)
    try {
      await camerasApi.probe(id)
      qc.invalidateQueries({ queryKey: ['cameras'] })
    } finally {
      setProbingId(null)
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h6" fontWeight={600}>Cameras</Typography>
          <Typography variant="body2" color="text.secondary">Manage RTSP camera streams</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
          Add Camera
        </Button>
      </Box>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>Add Camera</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 1 }}>
            Enter camera credentials and click <strong>Discover Streams</strong>, or paste a full RTSP URL directly.
          </DialogContentText>
          <CameraForm
            onSubmit={(data) => createMutation.mutate(data)}
            onCancel={() => setDialogOpen(false)}
            loading={createMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={!!editing} onClose={() => setEditing(null)} fullWidth maxWidth="md">
        <DialogTitle>Edit Camera</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 1 }}>Update camera details.</DialogContentText>
          {editing && (
            <CameraForm
              initial={{
                name: editing.name,
                ip_address: editing.ip_address ?? '',
                rtsp_url: editing.rtsp_url,
                sub_rtsp_url: editing.sub_rtsp_url ?? '',
                use_ffmpeg: editing.use_ffmpeg,
                use_sub_stream: editing.use_sub_stream,
                always_on: editing.always_on,
              }}
              onSubmit={(data) => updateMutation.mutate({ id: editing.id, data })}
              onCancel={() => setEditing(null)}
              loading={updateMutation.isPending}
            />
          )}
        </DialogContent>
      </Dialog>

      <TableContainer component={Paper} variant="outlined">
        {isLoading ? (
          <Typography variant="body2" color="text.disabled" sx={{ p: 3 }}>Loading...</Typography>
        ) : cameras.length === 0 ? (
          <Typography variant="body2" color="text.disabled" sx={{ p: 3 }}>No cameras yet. Add one to get started.</Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 80 }}>Order</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Main Stream</TableCell>
                <TableCell>Sub Stream</TableCell>
                <TableCell>Source</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {[...cameras].sort((a, b) => a.display_order - b.display_order || a.id - b.id).map((cam, index, sorted) => {
                const meta = cam.stream_metadata
                const isProbing = probingId === cam.id
                const sourceLabel = meta?.source === 'reolink_api' ? 'Reolink API' : meta?.source === 'ffprobe' ? 'ffprobe' : null

                return (
                  <TableRow key={cam.id}>
                    <TableCell>
                      <Stack direction="row" spacing={0}>
                        <Tooltip title="Move up">
                          <span>
                            <IconButton size="small" onClick={() => handleMove(index, 'up')} disabled={index === 0 || reorderMutation.isPending}>
                              <ArrowUpwardIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                        <Tooltip title="Move down">
                          <span>
                            <IconButton size="small" onClick={() => handleMove(index, 'down')} disabled={index === sorted.length - 1 || reorderMutation.isPending}>
                              <ArrowDownwardIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>{cam.name}</Typography>
                      <Typography variant="caption" fontFamily="monospace" color="text.disabled">
                        {cam.stream_path ?? '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" fontFamily="monospace" color={meta?.main ? 'text.primary' : 'text.disabled'}>
                        {streamLabel(meta?.main)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" fontFamily="monospace" color={meta?.sub ? 'text.primary' : 'text.disabled'}>
                        {cam.sub_rtsp_url ? streamLabel(meta?.sub) : '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap">
                        <Chip label={cam.use_ffmpeg ? 'FFmpeg' : 'Direct'} size="small" color={cam.use_ffmpeg ? 'warning' : 'default'} variant="outlined" />
                        {cam.sub_rtsp_url && <Chip label={cam.use_sub_stream ? 'Sub' : 'Main'} size="small" color={cam.use_sub_stream ? 'primary' : 'default'} variant="outlined" />}
                        {cam.always_on && <Chip label="Warm" size="small" color="success" variant="outlined" />}
                        {sourceLabel && <Chip label={sourceLabel} size="small" color="info" variant="outlined" />}
                      </Stack>
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title={meta ? 'Re-probe streams' : 'Probe streams'}>
                        <span>
                          <IconButton size="small" onClick={() => handleProbe(cam.id)} disabled={isProbing} color={meta ? 'success' : 'default'}>
                            {isProbing ? <CircularProgress size={16} /> : <RadarIcon fontSize="small" />}
                          </IconButton>
                        </span>
                      </Tooltip>
                      <IconButton size="small" onClick={() => setEditing(cam)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => { if (confirm(`Delete "${cam.name}"?`)) deleteMutation.mutate(cam.id) }}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </TableContainer>
    </Box>
  )
}
