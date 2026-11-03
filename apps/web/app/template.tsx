import type { ReactNode } from "react";

// Next monta la plantilla de nuevo en cada navegación: la entrada de la página va en CSS (.page).
// La barra está en el layout y no se mueve.
export default function Template({ children }: { children: ReactNode }) {
  return <div className="page">{children}</div>;
}
