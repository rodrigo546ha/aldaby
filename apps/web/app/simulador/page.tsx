import { Simulator } from "../../components/Simulator";

export const metadata = { title: "Simulador · Aldaby" };

export default function Home() {
  return (
    <main>
      <header className="intro">
        <h1>Tu plan de inversión</h1>
        <p>
          La rentabilidad con tu hipoteca, tu IRPF y tu ahorro. Cada cifra dice cómo se calcula
          y de qué norma o dato sale.
        </p>
      </header>
      <Simulator />
    </main>
  );
}
