import AcUnitIcon from '@mui/icons-material/AcUnit';
import PlumbingIcon from '@mui/icons-material/Plumbing';
import ElectricalServicesIcon from '@mui/icons-material/ElectricalServices';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import ChairIcon from '@mui/icons-material/Chair';
import CleaningServicesIcon from '@mui/icons-material/CleaningServices';
import BadgeIcon from '@mui/icons-material/Badge';
import WifiIcon from '@mui/icons-material/Wifi';
import ComputerIcon from '@mui/icons-material/Computer';
import PrintIcon from '@mui/icons-material/Print';
import VideocamIcon from '@mui/icons-material/Videocam';
import PhoneIcon from '@mui/icons-material/Phone';
import HelpOutlineIcon from '@mui/icons-material/HelpOutlineOutlined';
import type { SvgIconProps } from '@mui/material/SvgIcon';
import type { ComponentType } from 'react';

const ICONS: Record<string, ComponentType<SvgIconProps>> = {
  hvac: AcUnitIcon,
  plumbing: PlumbingIcon,
  electrical: ElectricalServicesIcon,
  lighting: LightbulbIcon,
  furniture: ChairIcon,
  cleaning: CleaningServicesIcon,
  access_security: BadgeIcon,
  network: WifiIcon,
  hardware: ComputerIcon,
  printer: PrintIcon,
  av_equipment: VideocamIcon,
  phone: PhoneIcon,
};

/** Icon for an incident category key (generic help icon for unknown/"other"). */
export default function CategoryIcon({ category, ...props }: { category: string } & SvgIconProps) {
  const Icon = ICONS[category] ?? HelpOutlineIcon;
  return <Icon {...props} />;
}
