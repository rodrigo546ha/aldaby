"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

// Recuento de visitas sin cookies (F8.6, ADR-0042): la ruta y, en la primera página, el dominio de
// origen y el utm_source. Nada se guarda en el navegador. Quien pide no ser rastreado no se cuenta.

function optedOut(): boolean {
  const nav = navigator as Navigator & { globalPrivacyControl?: boolean };
  return nav.globalPrivacyControl === true || nav.doNotTrack === "1";
}

export function VisitCounter() {
  const path = usePathname();
  const first = useRef(true);

  useEffect(() => {
    if (!path || optedOut()) return;
    const body: { path: string; referrer?: string; source?: string } = { path };
    if (first.current) {
      first.current = false;
      try {
        const from = document.referrer ? new URL(document.referrer) : null;
        if (from && from.host !== window.location.host) body.referrer = from.origin;
      } catch {
        // un referrer raro no se cuenta
      }
      const source = new URLSearchParams(window.location.search).get("utm_source");
      if (source) body.source = source;
    }
    const data = new Blob([JSON.stringify(body)], { type: "application/json" });
    if (!navigator.sendBeacon?.("/api/analytics/event", data)) {
      fetch("/api/analytics/event", { method: "POST", body: data, keepalive: true }).catch(() => undefined);
    }
  }, [path]);

  return null;
}
