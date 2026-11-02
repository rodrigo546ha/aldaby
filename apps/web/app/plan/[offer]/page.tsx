import { Plan } from "../../../components/Plan";

export const metadata = { title: "Plan · Aldaby" };

export default async function PlanPage({ params }: { params: Promise<{ offer: string }> }) {
  const { offer } = await params;
  return (
    <main>
      <header className="intro">
        <h1>Tu plan para esta oferta</h1>
        <p>
          Con tu hipoteca, tu IRPF y tu ahorro. Cada cifra dice cómo se calcula y de dónde sale;
          el asesor solo las explica.
        </p>
      </header>
      <Plan offerId={offer} />
    </main>
  );
}
