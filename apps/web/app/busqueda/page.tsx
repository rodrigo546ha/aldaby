import { Search } from "../../components/Search";

export const metadata = { title: "Supuestos · Aldaby" };

export default function SearchPage() {
  return (
    <main>
      <header className="intro">
        <h1>Tus supuestos</h1>
        <p>Lo que no tiene fuente pública y cambia tu plan en cada oferta: lo pones tú.</p>
      </header>
      <Search />
    </main>
  );
}
