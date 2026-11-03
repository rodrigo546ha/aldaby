import { Plan } from "../../../components/Plan";

export const metadata = { title: "Plan · Aldaby" };

export default async function PlanPage({ params }: { params: Promise<{ offer: string }> }) {
  const { offer } = await params;
  return (
    <main>
      <header className="intro">
        <h1>Tu plan para esta oferta</h1>
        <p>Con tu hipoteca, tu IRPF y tu ahorro. Cada tema guarda sus fórmulas y fuentes.</p>
      </header>
      <Plan offerId={offer} />
    </main>
  );
}
