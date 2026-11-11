"use client";

import { Fragment, useState, type CSSProperties, type ReactNode } from "react";

import type { components } from "../lib/api-types";
import { peek, seed, useApi } from "../lib/data";
import { closing, closingLabel, useNow } from "../lib/closing";
import { formatDate, formatShortDate, formatValue, type FigureOut } from "../lib/format";
import {
  CHANNEL,
  channelStyle,
  ending,
  formatArea,
  priceLabel,
  TYPE_LABEL,
  type CatalogOut,
} from "../lib/offers";
import { Amount } from "./FigureView";
import { Countdown } from "./Countdown";
import { ExplainHead, HowCalculated, Lede, Quote, SourceLink } from "./Explain";
import { Callout, Icon } from "./Icon";
import { Skeleton, Swap } from "./Motion";
import { OfferPhoto } from "./OfferPhoto";
import { AppLink, DATA } from "./AppLink";

type SearchOut = components["schemas"]["SearchOut"];
type ScoredOut = components["schemas"]["ScoredOut"];
type OfferScoreOut = components["schemas"]["OfferScoreOut"];
type BidsOut = components["schemas"]["BidsOut"];

// Ficha de una oferta (DESIGN.md, «Pantallas»): lo que decide arriba y en grande; tu plan al lado;
// la subasta, el inmueble y las fuentes debajo. Ninguna cifra se calcula aquí: vienen de la API.

type Plan =
  | { state: "cargando" }
  | { state: "ok"; scored: ScoredOut | null; skipped: string | null }
  | { state: "sin_plan"; code: number };

export function OfferDetail({ offerId }: { offerId: string }) {
  const offerUrl = `/api/offers/catalog/${offerId}`;
  const planUrl = `/api/search/offers/${offerId}`;
  // Si se llega desde el mapa, la oferta y su plan ya están en la caché: la ficha sale al momento
  useState(() => seedFromLists(offerId, offerUrl, planUrl));
  const offerApi = useApi<CatalogOut>(offerUrl);
  const planApi = useApi<OfferScoreOut>(planUrl);
  const now = useNow(60_000);
  const offer = offerApi.result?.ok ? offerApi.result.data : null;
  const failure =
    offerApi.result && !offerApi.result.ok
      ? offerApi.result.status === 404
        ? "No encontramos esta oferta, o no es de tu cuenta."
        : offerApi.result.status === 0
          ? "No se ha podido conectar con la API."
          : "No se ha podido cargar la oferta."
      : null;
  const plan: Plan = !planApi.result
    ? { state: "cargando" }
    : planApi.result.ok
      ? { state: "ok", scored: planApi.result.data.scored ?? null, skipped: planApi.result.data.skipped ?? null }
      : { state: "sin_plan", code: planApi.result.status };

  if (failure)
    return (
      <div className="offer-page">
        <AppLink className="back-link" href="/mapa" data={DATA.map()}>
          <Icon name="back" small /> Ofertas
        </AppLink>
        <Callout tone="danger">
          <p>{failure}</p>
        </Callout>
      </div>
    );
  if (!offer) return <Skeleton label="Cargando la oferta…" />;

  const when = ending(offer);
  const ended = offer.ends_on !== null && offer.ends_on !== undefined && offer.ends_on < new Date().toISOString().slice(0, 10);
  const soon = ended ? null : closingLabel(offer, now);
  const photos = offer.photos.length > 0 || offer.images.length > 0;

  return (
    <article className="offer-page" style={channelStyle(offer.channel)} aria-labelledby="oferta-titulo">
      <AppLink className="back-link" href="/mapa" data={DATA.map()}>
        <Icon name="back" small /> Ofertas
      </AppLink>

      <header className="offer-page-head">
        <div className="listing-top">
          <span className="ch-badge">{CHANNEL[offer.channel].label}</span>
          {offer.status === "por_confirmar" && <span className="tag warning">Por confirmar</span>}
          {ended ? (
            <span className="tag">Terminada</span>
          ) : soon ? (
            <span className="tag warning">
              <Icon name="clock" small /> {soon}
            </span>
          ) : (
            when && <span className="tag">{when}{offer.ends_time ? ` a las ${offer.ends_time}` : ""}</span>
          )}
        </div>
        <h1 id="oferta-titulo">{offer.title}</h1>
        {(offer.address || offer.place) && (
          <p className="offer-page-address">
            {offer.address ?? offer.place}
            {offer.address && offer.place && <span>{offer.place}</span>}
          </p>
        )}
      </header>

      {photos && (
        <div className="gallery">
          {offer.images.length > 0 && (
            <OfferPhoto offerId={offer.offer_id} kinds={[]} images={offer.images} credit hideEmpty morph />
          )}
          {offer.photos.map((kind, i) => (
            <OfferPhoto
              key={kind}
              offerId={offer.offer_id}
              kinds={[kind]}
              credit
              hideEmpty
              morph={i === 0 && offer.images.length === 0}
            />
          ))}
        </div>
      )}

      <KeyFacts offer={offer} when={ended ? "Terminada" : when} ended={ended} />

      <div className="offer-page-grid">
        <div className="offer-page-main">
          <Notices offer={offer} />
          {offer.auction ? <AuctionSection offer={offer} ended={ended} /> : <SaleSection offer={offer} />}
          <PropertySection offer={offer} />
          <SourcesSection offer={offer} />
        </div>
        <aside className="offer-page-aside" aria-label="Tu plan en esta oferta">
          <PlanCard offer={offer} plan={plan} />
        </aside>
      </div>
    </article>
  );
}

/** La oferta y su plan desde lo que ya trajo el mapa, para no esperar a pedirlos de nuevo. */
function seedFromLists(offerId: string, offerUrl: string, planUrl: string) {
  const list = peek<CatalogOut[]>("/api/offers/catalog");
  const item = list?.ok ? list.data.find((o) => o.offer_id === offerId) : undefined;
  if (item) seed(offerUrl, item);
  const search = peek<SearchOut>("/api/search");
  if (search?.ok) {
    const scored = search.data.ranked.find((s) => s.offer_id === offerId) ?? null;
    const skipped = search.data.skipped.find((s) => s.offer_id === offerId)?.reason ?? null;
    if (scored || skipped) seed<OfferScoreOut>(planUrl, { scored, skipped });
  }
}

function KeyFacts({ offer, when, ended }: { offer: CatalogOut; when: string | null; ended: boolean }) {
  // Con fecha de cierre y la subasta abierta, lo que queda; si no, la fecha que dé la fuente
  const close = ended ? null : closing(offer);
  const verb = offer.channel === "venta_directa" ? "El plazo acaba" : "Cierra";
  const facts: [string, ReactNode, string?][] = [];
  facts.push([priceLabel(offer), offer.price ? formatValue(offer.price, "EUR") : "Sin precio", offer.price ? undefined : "el anuncio no lo da"]);
  if (offer.deposit) facts.push(["Depósito para pujar", formatValue(offer.deposit, "EUR")]);
  if (offer.built_area_m2) facts.push(["Superficie construida", formatArea(offer.built_area_m2)]);
  if (close && offer.ends_on)
    facts.push([
      close.exact ? `${verb} en` : verb,
      <Countdown key="cierre" closing={close} date={offer.ends_on} />,
      `el ${formatShortDate(offer.ends_on)}${offer.ends_time ? ` a las ${offer.ends_time}` : ""}`,
    ]);
  else if (when) facts.push([offer.channel === "venta_directa" ? "Plazo" : "Subasta", when.replace(/^(Termina|Hasta) el /, ""), offer.ends_time ? `a las ${offer.ends_time}` : undefined]);
  return (
    <dl className="keyfacts">
      {facts.map(([label, value, note]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>
            {value}
            {note && <small>{note}</small>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function Notices({ offer }: { offer: CatalogOut }) {
  const list = [];
  if (offer.corrected)
    list.push(
      <Callout key="c" tone="warning">
        <p>
          <strong>El BOE publicó una corrección de este anuncio.</strong> Compruébala en la fuente antes de pujar: los datos
          de aquí salen del anuncio original.
        </p>
      </Callout>,
    );
  if (offer.habitual_residence)
    list.push(
      <Callout key="h" tone="warning">
        <p>
          <strong>Es la vivienda habitual del deudor.</strong> El remate tiene reglas propias: el simulador de puja de tu plan
          te dice qué pasa con cada puja.
        </p>
      </Callout>,
    );
  if (offer.approximate)
    list.push(
      <Callout key="a" tone="info">
        <p>
          <strong>Ubicación aproximada.</strong> La dirección del anuncio no se ha podido situar: el punto del mapa es el
          centro del municipio.
        </p>
      </Callout>,
    );
  if (offer.status === "por_confirmar")
    list.push(
      <Callout key="p" tone="info">
        <p>
          <strong>Faltan tus datos.</strong> Confirma lo que se ha leído del anuncio para calcular tu plan.{" "}
          <AppLink href={`/ofertas?id=${offer.offer_id}`}>Confirmar los datos</AppLink>
        </p>
      </Callout>,
    );
  return list.length > 0 ? <div className="notices">{list}</div> : null;
}

function AuctionSection({ offer, ended }: { offer: CatalogOut; ended: boolean }) {
  const live = offer.auction_state === "Celebrándose";
  const soon = offer.auction_state === "Próxima apertura";
  const facts = [
    ["Quién subasta", offer.authority],
    ["Procedimiento", offer.procedure],
    ["Depósito para pujar", offer.deposit ? formatValue(offer.deposit, "EUR") : null],
    ["Posesión", offer.possession],
    ["Visitas", offer.visitable],
    ["Vivienda habitual del deudor", offer.habitual_residence === null || offer.habitual_residence === undefined ? null : offer.habitual_residence ? "Sí" : "No"],
  ].filter((f): f is [string, string] => Boolean(f[1]));
  const steps = [
    offer.published_on && { what: "Publicada", when: formatDate(offer.published_on), state: "done" },
    (live || soon) && { what: live ? "Se puede pujar" : "Abre pronto", when: live ? "ahora" : "", state: live ? "now" : "now" },
    offer.ends_on && {
      what: ended ? "Cerró" : "Cierra",
      when: `${formatDate(offer.ends_on)}${offer.ends_time ? `, ${offer.ends_time}` : ""}`,
      state: ended ? "done" : "",
    },
  ].filter(Boolean) as { what: string; when: string; state: string }[];
  return (
    <section className="section-card" aria-labelledby="la-subasta">
      <header>
        <h2 id="la-subasta">La subasta</h2>
        <p>{CHANNEL[offer.channel].label}. Las cargas que subsisten se ven en la certificación de cargas del expediente.</p>
      </header>
      {steps.length > 0 && (
        <ol className="timeline" aria-label="Fechas de la subasta">
          {steps.map((s) => (
            <li key={s.what} className={s.state} aria-current={s.state === "now" ? "step" : undefined}>
              <span className="timeline-what">{s.what}</span>
              <span className="timeline-when">{s.when}</span>
            </li>
          ))}
        </ol>
      )}
      {facts.length > 0 && <Facts facts={facts} />}
    </section>
  );
}

function SaleSection({ offer }: { offer: CatalogOut }) {
  const facts = [
    [priceLabel(offer), offer.price ? formatValue(offer.price, "EUR") : null],
    ["Plazo para pedirla", offer.ends_on ? formatDate(offer.ends_on) : null],
    ["Publicada", offer.published_on ? formatDate(offer.published_on) : null],
  ].filter((f): f is [string, string] => Boolean(f[1]));
  if (facts.length === 0) return null;
  return (
    <section className="section-card" aria-labelledby="la-venta">
      <header>
        <h2 id="la-venta">{offer.channel === "venta_directa" ? "La venta directa" : "La venta"}</h2>
        {offer.channel === "venta_directa" && <p>Lote que quedó desierto en subasta: se vende por su precio de salida hasta el plazo.</p>}
      </header>
      <Facts facts={facts} />
    </section>
  );
}

function PropertySection({ offer }: { offer: CatalogOut }) {
  const facts = [
    ["Tipo", offer.property_type ? TYPE_LABEL[offer.property_type] ?? offer.property_type : null],
    ["Superficie construida", offer.built_area_m2 ? formatArea(offer.built_area_m2) : null],
    ["Año de construcción", offer.built_year ? String(offer.built_year) : null],
    ["Uso en el Catastro", offer.use],
    ["Planta", offer.floor],
    ["Referencia catastral", offer.cadastral_ref],
    ["Ubicación", offer.lon === null || offer.lon === undefined ? "Sin ubicar" : offer.approximate ? "Aproximada (centro del municipio)" : "En el mapa"],
  ].filter((f): f is [string, string] => Boolean(f[1]));
  return (
    <section className="section-card" aria-labelledby="el-inmueble">
      <h2 id="el-inmueble">El inmueble</h2>
      <Facts facts={facts} />
      {offer.description && (
        <div className="offer-quote">
          <ExplainHead>Cómo lo describe la fuente</ExplainHead>
          <Quote text={offer.description} cite={`Texto literal de ${offer.source_name ?? "la fuente"}`} />
        </div>
      )}
    </section>
  );
}

function SourcesSection({ offer }: { offer: CatalogOut }) {
  return (
    <section className="section-card" aria-labelledby="fuentes">
      <h2 id="fuentes">Fuentes</h2>
      <Lede>
        Los datos de la oferta salen de la fuente tal como los publica. Superficie, uso y año: Dirección General del
        Catastro.
      </Lede>
      {offer.source_url && (
        <SourceLink href={offer.source_url}>
          {offer.source_name === "Tu anuncio" ? "El anuncio" : `Ver en ${offer.source_name}`}
        </SourceLink>
      )}
      {offer.original_title && offer.original_title !== offer.title && (
        <p className="source-note">Título en la fuente: {offer.original_title}</p>
      )}
    </section>
  );
}

function Facts({ facts }: { facts: [string, string][] }) {
  return (
    <dl className="facts">
      {facts.map(([k, v]) => (
        <Fragment key={k}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </Fragment>
      ))}
    </dl>
  );
}

const fig = (s: ScoredOut, key: string): FigureOut | undefined => s.figures.find((f) => f.key === key);

function PlanCard({ offer, plan }: { offer: CatalogOut; plan: Plan }) {
  if (plan.state === "cargando")
    return (
      <section className="section-card plan-card" aria-busy="true">
        <h2>Tu plan</h2>
        <Skeleton label="Calculando tu plan en esta oferta…" shape="text" />
      </section>
    );
  if (plan.state === "sin_plan")
    return (
      <section className="section-card plan-card">
        <h2>Tu plan</h2>
        <p className="source-note">
          {plan.code === 409
            ? "Elige un cliente arriba para ver su plan en esta oferta."
            : "Completa tu perfil y verás si esta oferta encaja contigo: tu cuota, tu cash flow tras impuestos y tu rentabilidad."}
        </p>
        {plan.code !== 409 && (
          <AppLink className="button-link primary" href="/perfil">
            Completar el perfil
          </AppLink>
        )}
      </section>
    );
  const s = plan.scored;
  if (!s)
    return (
      <section className="section-card plan-card">
        <h2>Tu plan</h2>
        <p className="source-note">
          {plan.skipped
            ? `No se puede calcular: ${plan.skipped.replace(/\.$/, "").toLowerCase()}.`
            : offer.status === "por_confirmar"
              ? "Confirma los datos del anuncio para calcularlo."
              : "Esta oferta no entra en tu búsqueda."}
        </p>
      </section>
    );
  const shown = [
    ["cashflow.monthly_after_tax", "Tu cash flow"],
    ["irr.rate", "Rentabilidad (TIR)"],
    ["cashflow.cash_invested", "Lo que pones"],
  ] as const;
  return (
    <section className={`section-card plan-card ${s.passes ? "pass" : "fail"}`} aria-labelledby="tu-plan">
      <header>
        <h2 id="tu-plan">Tu plan</h2>
        <span className={s.passes ? "status pass" : "status fail"}>{s.passes ? "Encaja contigo" : "No encaja contigo"}</span>
      </header>
      <dl className="plan-card-figures">
        {shown.map(([key, label]) => {
          const f = fig(s, key);
          return f ? (
            <div key={key}>
              <dt>{label}</dt>
              <dd>
                <Amount text={formatValue(f.value, f.unit)} />
              </dd>
            </div>
          ) : null;
        })}
      </dl>
      {s.reasons.length > 0 && <p className="verdict-reason">{s.reasons.join(". ")}.</p>}
      <div className="verdict-actions">
        <AppLink className="button-link primary" href={`/plan/${offer.offer_id}`} data={DATA.plan(offer.offer_id)} morph>
          Ver mi plan completo
        </AppLink>
      </div>
      {offer.auction && <MaxBid offer={offer} />}
    </section>
  );
}

type BidState = { state: "sin_pedir" } | { state: "cargando" } | { state: "ok"; bids: BidsOut } | { state: "fallo"; text: string };

/**
 * Tu puja máxima en la ficha de una subasta. La calcula la API, que rehace el plan a cada puja
 * (ADR-0047); se pide al pulsar, porque cuenta como abrir el plan completo (ADR-0041). Aquí va sin
 * cargas ni coste de posesión: eso se ajusta en el simulador de puja del plan.
 */
function MaxBid({ offer }: { offer: CatalogOut }) {
  const key = `/api/plans/offers/${offer.offer_id}/bids`;
  const [bid, setBid] = useState<BidState>(() => {
    const kept = peek<BidsOut>(key);
    return kept?.ok ? { state: "ok", bids: kept.data } : { state: "sin_pedir" };
  });

  async function ask() {
    setBid({ state: "cargando" });
    try {
      const resp = await fetch(key, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ judicial: offer.channel === "subasta_judicial" }),
      });
      const body = await resp.json().catch(() => ({}));
      if (resp.ok) {
        seed<BidsOut>(key, body as BidsOut);
        setBid({ state: "ok", bids: body as BidsOut });
      } else {
        const detail = Array.isArray(body.detail) ? body.detail.join(". ") : body.detail;
        setBid({ state: "fallo", text: typeof detail === "string" ? detail : "No se ha podido calcular tu puja máxima." });
      }
    } catch {
      setBid({ state: "fallo", text: "No se ha podido conectar con la API." });
    }
  }

  const planLink = (
    <AppLink href={`/plan/${offer.offer_id}#pujas`} data={DATA.plan(offer.offer_id)} morph>
      Ajustar con cargas y posesión
    </AppLink>
  );
  if (bid.state !== "ok")
    return (
      <div className="maxbid">
        <button type="button" className="secondary" onClick={ask} disabled={bid.state === "cargando"}>
          <Swap>{bid.state === "cargando" ? "Calculando cada puja…" : "Calcular mi puja máxima"}</Swap>
        </button>
        {bid.state === "fallo" && <p className="failure">{bid.text}</p>}
      </div>
    );

  const { bids } = bid;
  const levels = [...bids.levels].sort((a, b) => Number(a.price.value) - Number(b.price.value));
  const top = Math.max(...levels.map((l) => Number(l.cashflow.value)), 0);
  return (
    <div className="maxbid">
      {bids.max_bid ? (
        <>
          <div className="maxbid-figure">
            <span className="maxbid-label">
              Tu puja máxima
              {bids.max_bid.provisional && <span className="prov-mark"> provisional</span>}
            </span>
            <span className="maxbid-value">
              <Amount text={formatValue(bids.max_bid.value, bids.max_bid.unit)} />
            </span>
          </div>
          <p className="source-note">
            Por encima, el plan deja de cumplir lo que pides. Va sin cargas ni coste de recuperar la posesión.
          </p>
        </>
      ) : (
        <p className="failure">Ni con la puja más baja cumple tu plan.</p>
      )}
      <ExplainHead>Tu cash flow al mes a cada puja</ExplainHead>
      <ol className="bid-levels">
        {levels.map((l, i) => {
          const cash = Number(l.cashflow.value);
          return (
            <li key={l.share} className={l.passes ? "pass" : "fail"} style={{ "--i": i } as CSSProperties}>
              <span className="bid-price">{formatValue(l.price.value, l.price.unit)}</span>
              <span className="bid-track" aria-hidden="true">
                <span className="bid-bar" style={{ width: `${top > 0 && cash > 0 ? Math.max((cash / top) * 100, 2) : 2}%` }} />
              </span>
              <span className="bid-cash">
                {formatValue(l.cashflow.value, "EUR")}
                {!l.passes && <small>no cumple</small>}
              </span>
            </li>
          );
        })}
      </ol>
      {bids.max_bid && (
        <details className="figure-how">
          <summary>Cómo se calcula</summary>
          <HowCalculated figure={bids.max_bid} />
        </details>
      )}
      {planLink}
    </div>
  );
}
