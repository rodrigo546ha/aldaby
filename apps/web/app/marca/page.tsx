import { BrandingEditor } from "../../components/Branding";

export const metadata = { title: "Tu marca · Aldaby" };

export default function BrandingPage() {
  return (
    <main>
      <header className="intro">
        <h1>Tu marca en los planes</h1>
        <p>
          Aparece en la cabecera del plan y del PDF que entregas a tus clientes. Al pie queda una
          línea discreta: «Cifras calculadas con Aldaby, con las fuentes del anexo».
        </p>
      </header>
      <BrandingEditor />
    </main>
  );
}
