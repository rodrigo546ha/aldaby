import { Profile } from "../../components/Profile";

export const metadata = { title: "Perfil · HouseFinder" };

export default function ProfilePage() {
  return (
    <main>
      <header className="intro">
        <h1>Tu perfil de inversor</h1>
        <p>
          Contesta con tus palabras; puedes dar varios datos en una respuesta. Te enseñamos de qué
          frase sale cada dato y cómo se ha calculado, y tú lo confirmas o lo corriges. Se guarda
          cifrado.
        </p>
      </header>
      <Profile />
    </main>
  );
}
