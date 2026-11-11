import Link from "next/link";

import { FreeTierLine, Waitlist } from "../components/Landing";
import { LandingHero, StepsJourney } from "../components/LandingHero";
import { Logo } from "../components/Logo";
import { SmoothScroll } from "../components/SmoothScroll";
import { ThemeToggle } from "../components/Theme";

export const metadata = {
  title: "Aldaby · Llama antes de comprar",
  description:
    "Lo que te rinde de verdad una vivienda de inversión: con tu hipoteca, tu IRPF y tus gastos. " +
    "Cada cifra con su fórmula y su fuente.",
};

// Página de presentación pública (F8.1, ADR-0041). Sin sesión: la lista de espera da el acceso.
export default function Landing() {
  return (
    <main className="landing">
      <SmoothScroll />
      <header className="landing-top">
        <Logo className="landing-logo" />
        <div className="landing-tools">
          <Link href="/acceso" className="landing-login">
            Ya tengo cuenta
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <LandingHero>
          <p className="hero-lead">
            Aldaby calcula lo que te rinde de verdad una vivienda de inversión: con tu hipoteca, tu
            IRPF, tus gastos y tu tiempo. No la rentabilidad del anuncio: la tuya.
          </p>
          <p className="hero-proof">Cada cifra lleva su fórmula y la norma o el dato público del que sale.</p>
          <a href="#lista" className="hero-cta">
            Apúntate a la lista de espera
          </a>
      </LandingHero>

      <section className="steps" aria-labelledby="como">
        <h2 id="como">Cómo funciona</h2>
        <StepsJourney>
        <ol>
          <li>
            <h3>Tu perfil</h3>
            <p>
              Una entrevista corta sobre tus ingresos, tus deudas y lo que buscas. Si subes una nómina
              o tu declaración, se lee en memoria y no se guarda: solo los datos, con la frase de la
              que salen.
            </p>
          </li>
          <li>
            <h3>Las ofertas</h3>
            <p>
              Subastas y ventas del BOE y del Patrimonio del Estado, la cartera de agencias que nos la
              ceden y cualquier anuncio que pegues. Cada una, ubicada en su barrio.
            </p>
          </li>
          <li>
            <h3>Tu plan</h3>
            <p>
              Cuánto puedes comprar, la cuota, el cash flow después de impuestos, qué pasa si suben
              los tipos o baja el alquiler, y los pasos para comprar. También en PDF.
            </p>
          </li>
        </ol>
        </StepsJourney>
      </section>

      <section className="principles">
        <div>
          <h2>Independiente</h2>
          <p>
            No vendemos inmuebles ni cobramos al vendedor por ponerlo arriba. Si alguna vez hay
            comisión, se dice en la oferta, y nunca cambia el orden: la recomendación es la mejor para
            ti.
          </p>
        </div>
        <div>
          <h2>Para profesionales</h2>
          <p>
            Asesores, intermediarios y agencias: un perfil por cliente, la búsqueda con su perfil y el
            plan con tu marca, listo para entregar.
          </p>
        </div>
        <div>
          <h2>Gratis para empezar</h2>
          <FreeTierLine />
        </div>
      </section>

      <section id="lista" className="waitlist" aria-labelledby="lista-titulo">
        <h2 id="lista-titulo">Lista de espera</h2>
        <p>
          Estamos abriendo poco a poco. Déjanos tu correo y te escribimos cuando haya sitio para ti.
        </p>
        <Waitlist />
      </section>

      <p className="landing-disclaimer">
        Aldaby calcula estimaciones con datos públicos y los que tú aportas. No presta asesoramiento
        financiero personalizado ni es intermediario de crédito inmobiliario.
      </p>
    </main>
  );
}
