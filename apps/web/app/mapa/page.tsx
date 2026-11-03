import { MapPage } from "../../components/MapPage";

export const metadata = { title: "Mapa · Aldaby" };

export default function Mapa() {
  return (
    <main className="map-page">
      <h1 className="visually-hidden">Ofertas en el mapa</h1>
      <MapPage />
    </main>
  );
}
