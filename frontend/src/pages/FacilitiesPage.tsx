import { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Collapse from '@mui/material/Collapse';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import Tooltip from '@mui/material/Tooltip';
import CircularProgress from '@mui/material/CircularProgress';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import ArchiveIcon from '@mui/icons-material/Archive';
import UnarchiveIcon from '@mui/icons-material/Unarchive';
import {
  listBuildings,
  listFloors,
  listSeats,
  deleteBuilding,
  deleteFloor,
  deleteSeat,
  updateBuilding,
  updateFloor,
  updateSeat,
} from '../services/facilityService';
import { ApiError } from '../services/apiClient';
import ErrorAlert from '../components/common/ErrorAlert';
import ConfirmDialog from '../components/common/ConfirmDialog';
import BuildingDialog from '../components/facilities/BuildingDialog';
import FloorDialog from '../components/facilities/FloorDialog';
import SeatDialog from '../components/facilities/SeatDialog';
import type { Building, Floor, Seat } from '../types';
import '../styles/facilities.css';

interface DeleteTarget {
  type: 'building' | 'floor' | 'seat';
  id: number;
  parentId?: number;
}

const DELETE_MESSAGES: Record<DeleteTarget['type'], string> = {
  building: 'This permanently deletes the building and all of its floors and seats.',
  floor: 'This permanently deletes the floor and all of its seats.',
  seat: 'This permanently deletes the seat.',
};

const ARCHIVE_MESSAGES: Record<DeleteTarget['type'], string> = {
  building: 'This archives the building, all of its floors and seats, and every incident reported there.',
  floor: 'This archives the floor, all of its seats, and every incident reported on it.',
  seat: 'This archives the seat and every incident reported at it.',
};

const ARCHIVE_EFFECT =
  ' Archived incidents are hidden from incident lists, dashboards and workloads and become read-only.' +
  ' The location is hidden from new reports. You can restore everything later.';

const HISTORY_NOTE = " Locations with incident history can't be deleted. Archive them instead.";

/** Small "Archived" marker shown next to archived buildings/floors. */
function ArchivedChip() {
  return <Chip label="Archived" size="small" variant="outlined" sx={{ ml: 1, height: 20, fontSize: '0.7rem' }} />;
}

export default function FacilitiesPage() {
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [floorsByBuilding, setFloorsByBuilding] = useState<Record<number, Floor[]>>({});
  const [seatsByFloor, setSeatsByFloor] = useState<Record<number, Seat[]>>({});
  const [expandedBuilding, setExpandedBuilding] = useState<number | null>(null);
  const [expandedFloor, setExpandedFloor] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [buildingDialog, setBuildingDialog] = useState<{ open: boolean; building: Building | null }>({
    open: false,
    building: null,
  });
  const [floorDialog, setFloorDialog] = useState<{ open: boolean; buildingId: number | null; floor: Floor | null }>({
    open: false,
    buildingId: null,
    floor: null,
  });
  const [seatDialog, setSeatDialog] = useState<{ open: boolean; floorId: number | null; seat: Seat | null }>({
    open: false,
    floorId: null,
    seat: null,
  });
  const [confirmDelete, setConfirmDelete] = useState<DeleteTarget | null>(null);
  // Set when a delete is blocked by incident history, to offer archiving instead.
  const [archiveSuggestion, setArchiveSuggestion] = useState<DeleteTarget | null>(null);
  const [confirmArchive, setConfirmArchive] = useState<DeleteTarget | null>(null);

  const loadBuildings = () => {
    setIsLoading(true);
    listBuildings(true)
      .then(setBuildings)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Unable to load buildings.'))
      .finally(() => setIsLoading(false));
  };

  useEffect(loadBuildings, []);

  const refreshFloors = (buildingId: number) => {
    listFloors(buildingId, true).then((floors) => setFloorsByBuilding((prev) => ({ ...prev, [buildingId]: floors })));
  };

  const refreshSeats = (floorId: number) => {
    listSeats(floorId, true).then((seats) => setSeatsByFloor((prev) => ({ ...prev, [floorId]: seats })));
  };

  const handleExpandBuilding = (buildingId: number) => {
    const next = expandedBuilding === buildingId ? null : buildingId;
    setExpandedBuilding(next);
    if (next && !floorsByBuilding[buildingId]) {
      refreshFloors(buildingId);
    }
  };

  const handleExpandFloor = (floorId: number) => {
    const next = expandedFloor === floorId ? null : floorId;
    setExpandedFloor(next);
    if (next && !seatsByFloor[floorId]) {
      refreshSeats(floorId);
    }
  };

  // Archiving cascades down the tree, so also refresh any floors/seats already loaded beneath the target.
  const refreshTarget = (target: DeleteTarget) => {
    if (target.type === 'building') {
      loadBuildings();
      if (floorsByBuilding[target.id]) refreshFloors(target.id);
      setSeatsByFloor({});
      setExpandedFloor(null);
    } else if (target.type === 'floor' && target.parentId) {
      refreshFloors(target.parentId);
      if (seatsByFloor[target.id]) refreshSeats(target.id);
    } else if (target.type === 'seat' && target.parentId) {
      refreshSeats(target.parentId);
    }
  };

  // Archiving asks for confirmation first (it cascades to incidents); restoring applies immediately.
  const requestArchive = (target: DeleteTarget, isArchived: boolean) => {
    setArchiveSuggestion(null);
    if (isArchived) setConfirmArchive(target);
    else setArchived(target, false);
  };

  const setArchived = async (target: DeleteTarget, isArchived: boolean) => {
    setError(null);
    setArchiveSuggestion(null);
    try {
      const update = { building: updateBuilding, floor: updateFloor, seat: updateSeat }[target.type];
      await update(target.id, { is_archived: isArchived });
      refreshTarget(target);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to update.');
    }
  };

  const handleConfirmedDelete = async () => {
    if (!confirmDelete) return;
    setError(null);
    setArchiveSuggestion(null);
    try {
      if (confirmDelete.type === 'building') {
        await deleteBuilding(confirmDelete.id);
        loadBuildings();
      } else if (confirmDelete.type === 'floor' && confirmDelete.parentId) {
        await deleteFloor(confirmDelete.id);
        refreshFloors(confirmDelete.parentId);
      } else if (confirmDelete.type === 'seat' && confirmDelete.parentId) {
        await deleteSeat(confirmDelete.id);
        refreshSeats(confirmDelete.parentId);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setArchiveSuggestion(confirmDelete);
      } else {
        setError(err instanceof ApiError ? err.message : 'Unable to delete.');
      }
    } finally {
      setConfirmDelete(null);
    }
  };

  return (
    <Box className="page-container">
      <Box className="flex-between" sx={{ mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4">Facilities</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setBuildingDialog({ open: true, building: null })}>
          Add building
        </Button>
      </Box>

      <ErrorAlert message={error} />
      {archiveSuggestion && (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          onClose={() => setArchiveSuggestion(null)}
          action={
            <Button color="inherit" size="small" onClick={() => requestArchive(archiveSuggestion, true)}>
              Archive instead
            </Button>
          }
        >
          This {archiveSuggestion.type} has incident history, so it can&apos;t be deleted. Archive it instead to hide it
          and its incidents without losing any data.
        </Alert>
      )}

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : buildings.length === 0 ? (
        <Typography color="text.secondary">No buildings yet. Add one to get started.</Typography>
      ) : (
        <div className="facility-tree">
          {buildings.map((building) => {
            const isExpanded = expandedBuilding === building.id;
            return (
              <Paper key={building.id} variant="outlined" sx={{ opacity: building.is_archived ? 0.7 : 1 }}>
                <Box
                  className="flex-between"
                  sx={{ p: 2, cursor: 'pointer' }}
                  onClick={() => handleExpandBuilding(building.id)}
                >
                  <Box>
                    <Typography variant="subtitle1">
                      {building.name}
                      {building.is_archived && <ArchivedChip />}
                    </Typography>
                    {building.address && (
                      <Typography variant="body2" color="text.secondary">
                        {building.address}
                      </Typography>
                    )}
                  </Box>
                  <Box className="flex-row" sx={{ gap: 0 }}>
                    <Box onClick={(e) => e.stopPropagation()} className="flex-row" sx={{ gap: 0 }}>
                      <IconButton size="small" onClick={() => setBuildingDialog({ open: true, building })}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <Tooltip title={building.is_archived ? 'Restore' : 'Archive'}>
                        <IconButton
                          size="small"
                          aria-label={building.is_archived ? 'Restore building' : 'Archive building'}
                          onClick={() => requestArchive({ type: 'building', id: building.id }, !building.is_archived)}
                        >
                          {building.is_archived ? <UnarchiveIcon fontSize="small" /> : <ArchiveIcon fontSize="small" />}
                        </IconButton>
                      </Tooltip>
                      <IconButton size="small" onClick={() => setConfirmDelete({ type: 'building', id: building.id })}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                    <ExpandMoreIcon
                      fontSize="small"
                      sx={{
                        color: 'action.active',
                        transform: isExpanded ? 'rotate(180deg)' : 'none',
                        transition: 'transform 150ms',
                      }}
                    />
                  </Box>
                </Box>
                <Collapse in={isExpanded}>
                  <Box sx={{ px: 2, pb: 2 }}>
                    <Button
                      size="small"
                      startIcon={<AddIcon />}
                      onClick={() => setFloorDialog({ open: true, buildingId: building.id, floor: null })}
                      sx={{ mb: 1 }}
                    >
                      Add floor
                    </Button>
                    {(floorsByBuilding[building.id] ?? []).length === 0 && (
                      <Typography variant="body2" color="text.secondary">
                        No floors yet.
                      </Typography>
                    )}
                    {(floorsByBuilding[building.id] ?? []).map((floor) => (
                      <div className="facility-floor-block" key={floor.id}>
                        <Box className="flex-between">
                          <Box sx={{ display: 'flex', alignItems: 'center', opacity: floor.is_archived ? 0.7 : 1 }}>
                            <Button size="small" onClick={() => handleExpandFloor(floor.id)}>
                              {floor.name}
                            </Button>
                            {floor.is_archived && <ArchivedChip />}
                          </Box>
                          <Box>
                            <Tooltip title={floor.is_archived ? 'Restore' : 'Archive'}>
                              <IconButton
                                size="small"
                                aria-label={floor.is_archived ? 'Restore floor' : 'Archive floor'}
                                onClick={() =>
                                  requestArchive({ type: 'floor', id: floor.id, parentId: building.id }, !floor.is_archived)
                                }
                              >
                                {floor.is_archived ? <UnarchiveIcon fontSize="small" /> : <ArchiveIcon fontSize="small" />}
                              </IconButton>
                            </Tooltip>
                            <IconButton size="small" onClick={() => setFloorDialog({ open: true, buildingId: building.id, floor })}>
                              <EditIcon fontSize="small" />
                            </IconButton>
                            <IconButton
                              size="small"
                              onClick={() => setConfirmDelete({ type: 'floor', id: floor.id, parentId: building.id })}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        </Box>
                        {expandedFloor === floor.id && (
                          <Box sx={{ mt: 1 }}>
                            <Button
                              size="small"
                              startIcon={<AddIcon />}
                              onClick={() => setSeatDialog({ open: true, floorId: floor.id, seat: null })}
                              sx={{ mb: 1 }}
                            >
                              Add seat
                            </Button>
                            <div className="facility-seat-chip-group">
                              {(seatsByFloor[floor.id] ?? []).map((seat) => (
                                <Chip
                                  key={seat.id}
                                  label={seat.is_archived ? `${seat.label} (archived)` : seat.label}
                                  variant={seat.is_archived ? 'outlined' : 'filled'}
                                  onClick={() => setSeatDialog({ open: true, floorId: floor.id, seat })}
                                  onDelete={() => setConfirmDelete({ type: 'seat', id: seat.id, parentId: floor.id })}
                                />
                              ))}
                              {(seatsByFloor[floor.id] ?? []).length === 0 && (
                                <Typography variant="body2" color="text.secondary">
                                  No seats yet.
                                </Typography>
                              )}
                            </div>
                          </Box>
                        )}
                      </div>
                    ))}
                  </Box>
                </Collapse>
              </Paper>
            );
          })}
        </div>
      )}

      <BuildingDialog
        open={buildingDialog.open}
        building={buildingDialog.building}
        onClose={() => setBuildingDialog({ open: false, building: null })}
        onSaved={loadBuildings}
      />
      <FloorDialog
        open={floorDialog.open}
        buildingId={floorDialog.buildingId}
        floor={floorDialog.floor}
        onClose={() => setFloorDialog({ open: false, buildingId: null, floor: null })}
        onSaved={() => floorDialog.buildingId && refreshFloors(floorDialog.buildingId)}
      />
      <SeatDialog
        open={seatDialog.open}
        floorId={seatDialog.floorId}
        seat={seatDialog.seat}
        onClose={() => setSeatDialog({ open: false, floorId: null, seat: null })}
        onSaved={() => seatDialog.floorId && refreshSeats(seatDialog.floorId)}
      />
      <ConfirmDialog
        open={Boolean(confirmArchive)}
        title={`Archive ${confirmArchive?.type ?? ''}`}
        message={confirmArchive ? `${ARCHIVE_MESSAGES[confirmArchive.type]}${ARCHIVE_EFFECT}` : ''}
        confirmLabel="Archive"
        confirmColor="primary"
        onCancel={() => setConfirmArchive(null)}
        onConfirm={() => {
          if (confirmArchive) setArchived(confirmArchive, true);
          setConfirmArchive(null);
        }}
      />
      <ConfirmDialog
        open={Boolean(confirmDelete)}
        title="Confirm delete"
        message={confirmDelete ? `${DELETE_MESSAGES[confirmDelete.type]}${HISTORY_NOTE}` : ''}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={handleConfirmedDelete}
      />
    </Box>
  );
}
