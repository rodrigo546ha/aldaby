import { LegalDocumentView } from "../../../components/Legal";

export const metadata = { title: "Textos legales · HouseFinder" };

export default async function LegalPage({ params }: { params: Promise<{ doc: string }> }) {
  const { doc } = await params;
  return (
    <main>
      <LegalDocumentView id={doc} />
    </main>
  );
}
