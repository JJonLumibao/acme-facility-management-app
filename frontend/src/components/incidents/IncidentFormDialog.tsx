import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import CircularProgress from '@mui/material/CircularProgress';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import { listBuildings, listFloors, listSeats } from '../../services/facilityService';
import { createIncident } from '../../services/incidentService';
import { ApiError } from '../../services/apiClient';
import { useCatalog } from '../../context/CatalogContext';
import ErrorAlert from '../common/ErrorAlert';
import CategoryPicker from './CategoryPicker';
import CategoryIcon from './CategoryIcon';
import { INCIDENT_PRIORITIES } from '../../types';
import { PRIORITY_HINTS, PRIORITY_LABELS } from '../../utils/format';
import type { Building, Floor, Incident, IncidentPriority, Seat } from '../../types';

const LAST_LOCATION_KEY = 'acme_last_incident_location';

interface SavedLocation {
  buildingId: string;
  floorId: string;
  seatId: string;
}

function readLastLocation(): SavedLocation | null {
  try {
    const raw = localStorage.getItem(LAST_LOCATION_KEY);
    return raw ? (JSON.parse(raw) as SavedLocation) : null;
  } catch {
    return null;
  }
}

function saveLastLocation(location: SavedLocation): void {
  try {
    localStorage.setItem(LAST_LOCATION_KEY, JSON.stringify(location));
  } catch {
    // Storage unavailable (private mode etc.) - remembering the location is just a convenience.
  }
}

interface IncidentFormDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (incident: Incident) => void;
}

/**
 * Two-step incident report: (1) pick what kind of problem it is from category tiles,
 * (2) describe it, confirm the location (pre-filled with the last one used) and pick urgency.
 */
export default function IncidentFormDialog({ open, onClose, onCreated }: IncidentFormDialogProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { catalog, getCategory } = useCatalog();

  const [step, setStep] = useState<'category' | 'details'>('category');
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [floors, setFloors] = useState<Floor[]>([]);
  const [seats, setSeats] = useState<Seat[]>([]);
  const [category, setCategory] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<IncidentPriority>('medium');
  const [buildingId, setBuildingId] = useState('');
  const [floorId, setFloorId] = useState('');
  const [seatId, setSeatId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadFloors = (id: string) =>
    id ? listFloors(Number(id)).then(setFloors).catch(() => setFloors([])) : Promise.resolve(setFloors([]));
  const loadSeats = (id: string) =>
    id ? listSeats(Number(id)).then(setSeats).catch(() => setSeats([])) : Promise.resolve(setSeats([]));

  // On open: load buildings and restore the reporter's last-used location if it still exists.
  useEffect(() => {
    if (!open) return;
    listBuildings()
      .then(async (loaded) => {
        setBuildings(loaded);
        const last = readLastLocation();
        if (!last || !loaded.some((building) => String(building.id) === last.buildingId)) return;
        setBuildingId(last.buildingId);
        const loadedFloors = await listFloors(Number(last.buildingId)).catch(() => [] as Floor[]);
        setFloors(loadedFloors);
        if (!loadedFloors.some((floor) => String(floor.id) === last.floorId)) return;
        setFloorId(last.floorId);
        const loadedSeats = await listSeats(Number(last.floorId)).catch(() => [] as Seat[]);
        setSeats(loadedSeats);
        if (loadedSeats.some((seat) => String(seat.id) === last.seatId)) setSeatId(last.seatId);
      })
      .catch(() => setBuildings([]));
  }, [open]);

  const handleBuildingChange = (id: string) => {
    setBuildingId(id);
    setFloorId('');
    setSeatId('');
    setSeats([]);
    loadFloors(id);
  };

  const handleFloorChange = (id: string) => {
    setFloorId(id);
    setSeatId('');
    loadSeats(id);
  };

  const handleCategoryPick = (key: string) => {
    setCategory(key);
    setStep('details');
  };

  const resetForm = () => {
    setStep('category');
    setCategory('');
    setTitle('');
    setDescription('');
    setPriority('medium');
    setBuildingId('');
    setFloorId('');
    setSeatId('');
    setFloors([]);
    setSeats([]);
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const incident = await createIncident({
        title: title.trim(),
        category,
        description: description.trim() || undefined,
        priority,
        building_id: Number(buildingId),
        floor_id: floorId ? Number(floorId) : undefined,
        seat_id: seatId ? Number(seatId) : undefined,
      });
      saveLastLocation({ buildingId, floorId, seatId });
      onCreated(incident);
      handleClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to create incident.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedCategory = getCategory(category);

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="md" fullScreen={isMobile}>
      <form onSubmit={handleSubmit}>
        <DialogTitle>{step === 'category' ? 'What kind of problem is it?' : 'Tell us more'}</DialogTitle>
        <DialogContent dividers>
          <ErrorAlert message={error} />
          {step === 'category' ? (
            catalog ? (
              <CategoryPicker categories={catalog.categories} value={category} onChange={handleCategoryPick} />
            ) : (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            )
          ) : (
            <Stack spacing={2.5}>
              <Box className="flex-row" sx={{ gap: 1, flexWrap: 'wrap' }}>
                <CategoryIcon category={category} color="primary" />
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                  {selectedCategory?.label ?? category}
                </Typography>
                <Button size="small" onClick={() => setStep('category')}>
                  Change
                </Button>
              </Box>
              <TextField
                label="Short summary"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                fullWidth
                autoFocus
                placeholder={selectedCategory ? `e.g. ${selectedCategory.description.split(',')[0]}` : ''}
                slotProps={{ htmlInput: { maxLength: 120 } }}
              />
              <TextField
                label="Details (optional)"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                fullWidth
                multiline
                minRows={2}
                placeholder="What happened, since when, and anything you've already tried"
              />

              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Where is it?
                </Typography>
                <Box className="incident-location-fields">
                  <TextField
                    select
                    label="Building"
                    value={buildingId}
                    onChange={(e) => handleBuildingChange(e.target.value)}
                    required
                    fullWidth
                  >
                    {buildings.map((b) => (
                      <MenuItem key={b.id} value={String(b.id)}>
                        {b.name}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    select
                    label="Floor"
                    value={floorId}
                    onChange={(e) => handleFloorChange(e.target.value)}
                    fullWidth
                    disabled={!buildingId || floors.length === 0}
                  >
                    <MenuItem value="">Not specific</MenuItem>
                    {floors.map((f) => (
                      <MenuItem key={f.id} value={String(f.id)}>
                        {f.name}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    select
                    label="Seat / room"
                    value={seatId}
                    onChange={(e) => setSeatId(e.target.value)}
                    fullWidth
                    disabled={!floorId || seats.length === 0}
                  >
                    <MenuItem value="">Not specific</MenuItem>
                    {seats.map((s) => (
                      <MenuItem key={s.id} value={String(s.id)}>
                        {s.label}
                      </MenuItem>
                    ))}
                  </TextField>
                </Box>
              </Box>

              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  How urgent is it?
                </Typography>
                <ToggleButtonGroup
                  exclusive
                  size="small"
                  value={priority}
                  onChange={(_, value: IncidentPriority | null) => value && setPriority(value)}
                  sx={{ flexWrap: 'wrap' }}
                >
                  {INCIDENT_PRIORITIES.map((p) => (
                    <ToggleButton key={p} value={p} sx={{ px: 2 }}>
                      {PRIORITY_LABELS[p]}
                    </ToggleButton>
                  ))}
                </ToggleButtonGroup>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  {PRIORITY_HINTS[priority]}
                </Typography>
              </Box>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          {step === 'details' && (
            <Button type="submit" variant="contained" disabled={isSubmitting || !title.trim() || !buildingId}>
              {isSubmitting ? <CircularProgress size={20} color="inherit" /> : 'Submit report'}
            </Button>
          )}
        </DialogActions>
      </form>
    </Dialog>
  );
}
