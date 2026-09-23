import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { getCatalog } from '../services/catalogService';
import type { Catalog, Category } from '../types';

interface CatalogContextValue {
  catalog: Catalog | null;
  categoryLabel: (key: string) => string;
  departmentLabel: (key: string | null | undefined) => string;
  getCategory: (key: string) => Category | undefined;
}

const CatalogContext = createContext<CatalogContextValue | undefined>(undefined);

/** Loads reference data (categories, departments, workflow) once for all authenticated pages. */
export function CatalogProvider({ children }: { children: ReactNode }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);

  useEffect(() => {
    getCatalog()
      .then(setCatalog)
      .catch(() => setCatalog(null));
  }, []);

  const getCategory = useCallback(
    (key: string) => catalog?.categories.find((category) => category.key === key),
    [catalog],
  );

  // Unknown keys (e.g. free-text categories from before the fixed list existed) fall back to a readable form.
  const categoryLabel = useCallback(
    (key: string) => getCategory(key)?.label ?? key.replace(/_/g, ' '),
    [getCategory],
  );

  const departmentLabel = useCallback(
    (key: string | null | undefined) =>
      key ? (catalog?.departments.find((department) => department.key === key)?.label ?? key) : 'No department',
    [catalog],
  );

  const value = useMemo(
    () => ({ catalog, categoryLabel, departmentLabel, getCategory }),
    [catalog, categoryLabel, departmentLabel, getCategory],
  );

  return <CatalogContext.Provider value={value}>{children}</CatalogContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components -- hook is intentionally co-located with its provider
export function useCatalog(): CatalogContextValue {
  const context = useContext(CatalogContext);
  if (!context) {
    throw new Error('useCatalog must be used within a CatalogProvider');
  }
  return context;
}
