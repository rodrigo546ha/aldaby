import { Suspense } from "react";

import { ChoosePassword } from "../../../components/Access";

export const metadata = { title: "Elige tu contraseña · Aldaby" };

export default function PasswordPage() {
  return (
    <main className="access">
      <header className="intro">
        <h1>Elige tu contraseña</h1>
        <p>Al menos doce caracteres. Una frase que recuerdes vale más que una palabra rara.</p>
      </header>
      <Suspense>
        <ChoosePassword />
      </Suspense>
    </main>
  );
}
