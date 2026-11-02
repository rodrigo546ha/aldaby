import { Feeds } from "../../components/Feeds";

export const metadata = { title: "Agencias · HouseFinder" };

export default function AgenciesPage() {
  return (
    <main>
      <header className="intro">
        <h1>Agencias</h1>
        <p>
          La cartera de las agencias que te ceden su feed. Con su consentimiento por escrito, la
          herramienta lee cada mañana los inmuebles en venta y los analiza en la búsqueda con el
          perfil de tu cliente.
        </p>
      </header>
      <Feeds />
    </main>
  );
}
