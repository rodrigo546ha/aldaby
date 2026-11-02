import { Suspense } from "react";

import { LegalAcceptance } from "../../../components/Legal";

export const metadata = { title: "Condiciones · Aldaby" };

export default function AcceptancePage() {
  return (
    <main className="access">
      <header className="intro">
        <h1>Condiciones y privacidad</h1>
        <p>
          Para usar la herramienta hace falta aceptar la versión vigente de estos textos. Si cambian,
          te los volveremos a pedir.
        </p>
      </header>
      <Suspense>
        <LegalAcceptance />
      </Suspense>
    </main>
  );
}
