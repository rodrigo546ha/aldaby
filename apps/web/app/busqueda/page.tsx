import { Search } from "../../components/Search";

export const metadata = { title: "Búsqueda · Aldaby" };

export default function SearchPage() {
  return (
    <main>
      <header className="intro">
        <h1>Ofertas que encajan contigo</h1>
        <p>
          Tu plan en cada oferta: con tu hipoteca, tu IRPF y tu ahorro. Pasan las que cumplen tu
          capacidad, tu cash flow mínimo y tu riesgo, ordenadas por tu objetivo.
        </p>
      </header>
      <Search />
    </main>
  );
}
