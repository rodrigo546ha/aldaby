import { Announcements } from "../../components/Announcements";

export const metadata = { title: "Anuncios del BOE · HouseFinder" };

export default function AnnouncementsPage() {
  return (
    <main>
      <header className="intro">
        <h1>Anuncios del BOE</h1>
        <p>
          Ventas y subastas de inmuebles del Estado publicadas en el BOE. Los datos de cada lote
          los extrae un modelo y van con la frase de la que salen: compruébalos antes de usarlos.
        </p>
      </header>
      <Announcements />
    </main>
  );
}
