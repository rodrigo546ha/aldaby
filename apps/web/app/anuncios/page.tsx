import { redirect } from "next/navigation";

// Los lotes del BOE y del Patrimonio están en la lista única de ofertas (ADR-0054)
export default function AnnouncementsPage() {
  redirect("/mapa");
}
