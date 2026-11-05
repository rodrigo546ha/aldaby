import { Offers } from "../../components/Offers";

export const metadata = { title: "Añadir un anuncio · Aldaby" };

export default function OffersPage() {
  return (
    <main>
      <header className="intro">
        <h1>Añadir un anuncio</h1>
        <p>De cualquier portal o agencia: lo leemos, lo revisas y entra en tus ofertas con tu plan.</p>
      </header>
      <Offers />
    </main>
  );
}
