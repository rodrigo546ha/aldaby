import { Suspense } from "react";

import { Login } from "../../components/Access";

export const metadata = { title: "Acceso · HouseFinder" };

export default function AccessPage() {
  return (
    <main className="access">
      <header className="intro">
        <h1>Entra en HouseFinder</h1>
        <p>Beta privada: la cuenta te la da el equipo de HouseFinder.</p>
      </header>
      <Suspense>
        <Login />
      </Suspense>
    </main>
  );
}
