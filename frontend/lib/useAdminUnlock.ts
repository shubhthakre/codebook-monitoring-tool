"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const STORAGE_KEY = "st-monitoring-admin";

// Survives client-side navigation, resets on full page refresh.
let adminUnlocked = false;

export function useAdminUnlock() {
  const [unlocked, setUnlocked] = useState(adminUnlocked);
  const clicksRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore storage errors
    }
  }, []);

  const handleTitleClick = useCallback(() => {
    if (unlocked) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    clicksRef.current += 1;
    if (clicksRef.current >= 5) {
      clicksRef.current = 0;
      adminUnlocked = true;
      setUnlocked(true);
      return;
    }
    timerRef.current = setTimeout(() => {
      clicksRef.current = 0;
    }, 2000);
  }, [unlocked]);

  return { unlocked, ready: true, handleTitleClick };
}
