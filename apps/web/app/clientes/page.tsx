import { Clients } from "../../components/Clients";

export const metadata = { title: "Clientes · HouseFinder" };

export default function ClientsPage() {
  return (
    <main>
      <header className="intro">
        <h1>Tus clientes</h1>
        <p>
          Cada cliente tiene su perfil, su búsqueda y su plan. Elige arriba con cuál trabajas;
          las ofertas que pegues sirven para todos.
        </p>
      </header>
      <Clients />
    </main>
  );
}
