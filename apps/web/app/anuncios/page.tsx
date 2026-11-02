import { PublicOffers } from "../../components/PublicOffers";

export const metadata = { title: "Anuncios públicos · HouseFinder" };

export default function AnnouncementsPage() {
  return (
    <main>
      <header className="intro">
        <h1>Anuncios públicos</h1>
        <p>
          Ventas y subastas de inmuebles del Estado: las que se publican en el BOE y las ventas
          directas del Patrimonio del Estado. Los datos de cada lote los extrae un modelo y van con
          la frase de la que salen: compruébalos antes de usarlos.
        </p>
      </header>
      <PublicOffers />
    </main>
  );
}
