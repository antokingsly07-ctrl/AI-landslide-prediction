import { useEffect, useState } from "react";

export function useOnline() {
  const [online, setOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}

export function useInterval(cb: () => void, ms: number | null) {
  useEffect(() => {
    if (ms === null) return;
    const id = setInterval(cb, ms);
    return () => clearInterval(id);
  }, [cb, ms]);
}
