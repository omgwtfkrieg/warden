import { useQuery } from '@tanstack/react-query'
import { Box, Card, CardContent, Grid, Typography, Divider } from '@mui/material'
import CameraAltIcon from '@mui/icons-material/CameraAlt'
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid'
import WifiIcon from '@mui/icons-material/Wifi'
import { camerasApi } from '@/api/cameras'
import { devicesApi } from '@/api/devices'
import { api } from '@/api/client'

function StatCard({ icon, label, value }: {
  icon: React.ReactNode
  label: string
  value: number | string
}) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">{label}</Typography>
          <Box sx={{ color: 'text.disabled' }}>{icon}</Box>
        </Box>
        <Typography variant="h4" fontWeight={700}>{value}</Typography>
      </CardContent>
    </Card>
  )
}

export function DashboardPage() {
  const { data: cameras } = useQuery({ queryKey: ['cameras'], queryFn: camerasApi.list })
  const { data: devices } = useQuery({ queryKey: ['devices'], queryFn: devicesApi.list })
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.get('/health').then((r) => r.data as { status: string }),
    refetchInterval: 30_000,
  })

  const activeDevices = devices?.filter((d) => !d.revoked).length ?? 0

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" fontWeight={600} gutterBottom>Dashboard</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>System overview</Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <StatCard icon={<CameraAltIcon />} label="Cameras" value={cameras?.length ?? '—'} />
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatCard icon={<PhoneAndroidIcon />} label="Active Devices" value={activeDevices} />
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatCard
            icon={<WifiIcon />}
            label="API Status"
            value={health?.status === 'ok' ? 'Online' : 'Offline'}
          />
        </Grid>
      </Grid>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 1.5 }}>Recent Cameras</Typography>
          <Divider sx={{ mb: 1.5 }} />
          {cameras?.length ? (
            cameras.slice(0, 5).map((c) => (
              <Box key={c.id} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.75 }}>
                <Typography variant="body2">{c.name}</Typography>
                <Typography variant="caption" color="text.disabled" fontFamily="monospace">{c.stream_path}</Typography>
              </Box>
            ))
          ) : (
            <Typography variant="body2" color="text.disabled">No cameras configured yet.</Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}
