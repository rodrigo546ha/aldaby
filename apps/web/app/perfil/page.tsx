import { Profile } from "../../components/Profile";

export const metadata = { title: "Perfil · Aldaby" };

export default function ProfilePage() {
  return (
    <main>
      <header className="intro">
        <h1>Tu perfil de inversor</h1>
        <p>Con él se calcula tu plan en cada oferta: tu hipoteca, tu IRPF y tu ahorro.</p>
      </header>
      <Profile />
    </main>
  );
}
