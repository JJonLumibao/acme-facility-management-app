import ButtonBase from '@mui/material/ButtonBase';
import Typography from '@mui/material/Typography';
import CategoryIcon from './CategoryIcon';
import type { Category } from '../../types';
import '../../styles/incidents.css';

const GROUPS: Array<{ key: Category['group']; label: string }> = [
  { key: 'facility', label: 'Facility' },
  { key: 'technology', label: 'Workplace technology' },
  { key: 'other', label: 'Something else' },
];

interface CategoryPickerProps {
  categories: Category[];
  value: string;
  onChange: (key: string) => void;
}

/** Grid of tappable category tiles grouped by facility vs technology. */
export default function CategoryPicker({ categories, value, onChange }: CategoryPickerProps) {
  return (
    <div className="category-picker">
      {GROUPS.map((group) => {
        const items = categories.filter((category) => category.group === group.key);
        if (items.length === 0) return null;
        return (
          <section key={group.key}>
            <Typography variant="overline" color="text.secondary" component="h3">
              {group.label}
            </Typography>
            <div className="category-grid">
              {items.map((category) => (
                <ButtonBase
                  key={category.key}
                  className={`category-tile${value === category.key ? ' category-tile-selected' : ''}`}
                  onClick={() => onChange(category.key)}
                  aria-pressed={value === category.key}
                  focusRipple
                >
                  <CategoryIcon category={category.key} color={value === category.key ? 'primary' : 'action'} />
                  <span className="category-tile-label">{category.label}</span>
                  <span className="category-tile-hint">{category.description}</span>
                </ButtonBase>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
