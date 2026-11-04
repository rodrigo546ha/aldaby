import { MapPage } from "../../components/MapPage";

export const metadata = { title: "Ofertas · Aldaby" };

export default function Mapa() {
  return (
    <main className="map-page">
      <h1 className="visually-hidden">Ofertas</h1>
      <MapPage />
    </main>
  );
}
