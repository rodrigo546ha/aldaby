import { Offers } from "../../components/Offers";

export const metadata = { title: "Ofertas · Aldaby" };

export default function OffersPage() {
  return (
    <main>
      <header className="intro">
        <h1>Analiza un anuncio</h1>
        <p>
          Pega el enlace de un anuncio o su texto. Extraemos los datos y te enseñamos de qué frase
          sale cada uno; tú los confirmas o los corriges antes de usarlos en tu plan.
        </p>
      </header>
      <Offers />
    </main>
  );
}
