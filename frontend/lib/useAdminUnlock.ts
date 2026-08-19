"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const STORAGE_KEY = "st-monitoring-admin";

export function useAdminUnlock() {
  const [unlocked, setUnlocked] = useState(false);
  const [ready, setReady] = useState(false);
  const clicksRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    try {
      if (sessionStorage.getItem(STORAGE_KEY) === "1") {
        setUnlocked(true);
      }
    } catch {
      // ignore storage errors
    } finally {
      setReady(true);
    }
  }, []);

  const handleTitleClick = useCallback(() => {
    if (unlocked) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    clicksRef.current += 1;
    if (clicksRef.current >= 5) {
      clicksRef.current = 0;
      setUnlocked(true);
      try {
        sessionStorage.setItem(STORAGE_KEY, "1");
      } catch {
        // ignore storage errors
      }
      return;
    }
    timerRef.current = setTimeout(() => {
      clicksRef.current = 0;
    }, 2000);
  }, [unlocked]);

  return { unlocked, ready, handleTitleClick };
}
