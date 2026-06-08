import React, { createContext, useContext } from 'react';
import { useHybrid } from './hooks/useHybrid';

const Ctx = createContext(null);

export function HybridProvider({ children }) {
  const data = useHybrid();
  return <Ctx.Provider value={data}>{children}</Ctx.Provider>;
}

export function useGhostGoat() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useGhostGoat must be inside HybridProvider');
  return ctx;
}
