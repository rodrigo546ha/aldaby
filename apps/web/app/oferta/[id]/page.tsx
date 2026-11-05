import { OfferDetail } from "../../../components/OfferDetail";

export const metadata = { title: "Oferta · Aldaby" };

export default async function OfferPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main>
      <OfferDetail offerId={id} />
    </main>
  );
}
