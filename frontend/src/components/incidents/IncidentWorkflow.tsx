import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Chip from '@mui/material/Chip';
import type { IncidentStatus } from '../../types';
import '../../styles/incidents.css';

const STEPS: Array<{ key: IncidentStatus; label: string }> = [
  { key: 'open', label: 'Open' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'resolved', label: 'Resolved' },
  { key: 'closed', label: 'Closed' },
];

/** Visualizes the incident workflow as a stepper; "blocked" renders as a red marker mid-flow. */
export default function IncidentWorkflow({ status }: { status: IncidentStatus }) {
  const isBlocked = status === 'blocked';
  const effectiveStatus = isBlocked ? 'in_progress' : status;
  const activeIndex = STEPS.findIndex((step) => step.key === effectiveStatus);

  return (
    <div className="incident-workflow">
      <Stepper activeStep={activeIndex} alternativeLabel>
        {STEPS.map((step, index) => (
          <Step key={step.key} completed={index < activeIndex}>
            <StepLabel error={isBlocked && index === activeIndex} className={isBlocked && index === activeIndex ? 'incident-workflow-blocked' : ''}>
              {step.label}
            </StepLabel>
          </Step>
        ))}
      </Stepper>
      {isBlocked && (
        <Chip label="Blocked" color="error" size="small" sx={{ display: 'block', mx: 'auto', mt: 1, width: 'fit-content' }} />
      )}
    </div>
  );
}
