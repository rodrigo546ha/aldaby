// Solo formatea: la web nunca calcula cifras (D11). Los valores llegan de la API como texto.
import type { components } from "./api-types";

export type FigureOut = components["schemas"]["FigureOut"];

const eur = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" });
const pct = new Intl.NumberFormat("es-ES", { style: "percent", maximumFractionDigits: 2 });
const years = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 1 });

export function formatValue(value: string, unit: string): string {
  const n = Number(value);
  switch (unit) {
    case "EUR":
      return eur.format(n);
    case "EUR/mes":
      return `${eur.format(n)} al mes`;
    case "EUR/año":
      return `${eur.format(n)} al año`;
    case "EUR/m2":
      return `${eur.format(n)}/m²`;
    case "EUR/m2 mes":
      return `${eur.format(n)}/m² al mes`;
    case "ratio":
      return pct.format(n);
    case "años":
      return `${years.format(n)} años`;
    default:
      return `${value} ${unit}`;
  }
}

/** "3,5" (por ciento) → "0.035" (tanto por uno), moviendo la coma en el texto, sin floats. */
export function percentToRatio(text: string): string | null {
  const clean = text.trim().replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(clean)) return null;
  const [int, frac = ""] = clean.split(".");
  const padded = int.padStart(3, "0");
  return `${padded.slice(0, -2)}.${padded.slice(-2)}${frac}`;
}

/** Importe escrito con coma o punto decimal → texto para la API. */
export function amount(text: string): string | null {
  const clean = text.trim().replace(/\s/g, "").replace(",", ".");
  return /^\d+(\.\d+)?$/.test(clean) ? clean : null;
}

export const SOURCE_KIND: Record<string, string> = {
  rule: "Norma",
  param: "Parámetro",
  dataset: "Datos",
  model: "Modelo",
  user_input: "Dato tuyo",
  assumption: "Supuesto",
};

export const LABELS: Record<string, string> = {
  "affordability.max_price": "Precio máximo",
  "affordability.max_loan": "Préstamo máximo",
  "affordability.max_payment": "Cuota máxima",
  "affordability.years": "Plazo máximo",
  "purchase_costs.transfer_tax": "Impuesto de compra (ITP)",
  "purchase_costs.vat": "IVA",
  "purchase_costs.stamp_duty": "Actos jurídicos documentados (AJD)",
  "purchase_costs.notary": "Notaría (escritura)",
  "purchase_costs.registry": "Registro de la propiedad",
  "purchase_costs.regulated": "Gastos que fija la normativa",
  "purchase_costs.other": "Gestoría, tasación y copias",
  "purchase_costs.total": "Gastos de compra",
  "financing.loan": "Préstamo",
  "financing.years": "Plazo",
  "mortgage.monthly_payment": "Cuota",
  "mortgage.stressed_payment": "Cuota con subida de tipos",
  "holding_costs.ibi_annual": "IBI",
  "cashflow.gross_yield": "Rentabilidad bruta",
  "cashflow.annual_operating": "Cash flow antes de impuestos",
  "cashflow.annual_tax": "IRPF por el alquiler",
  "cashflow.monthly_after_tax": "Cash flow tras impuestos",
  "cashflow.cash_invested": "Dinero aportado",
  "cashflow.cash_on_cash": "Cash-on-cash",
  "term.recommended_years": "Plazo recomendado",
  "term.stressed_monthly_payment": "Cuota en estrés al plazo recomendado",
  "term.stressed_monthly_cashflow": "Cash flow en estrés al plazo recomendado",
  "irr.rate": "TIR",
  "irr.rate_conservative": "TIR en el escenario conservador",
  "irr.rate_optimistic": "TIR en el escenario optimista",
  "valuation.rent_monthly": "Renta estimada",
  "valuation.rent_m2_month": "Renta por m²",
  "valuation.price_total": "Precio estimado",
  "valuation.price_m2": "Precio por m²",
  "valuation.price_rent_ratio": "Años de renta que vale (municipio)",
  "offer.asking_gap": "Precio pedido frente al estimado",
  "offer.gross_yield_at_asking": "Rentabilidad bruta al precio pedido",
  "offer.asking_rent_gap": "Renta pedida frente a la estimada",
  "valuation.appreciation_conservative": "Revalorización anual, conservador",
  "valuation.appreciation_base": "Revalorización anual, base",
  "valuation.appreciation_optimistic": "Revalorización anual, optimista",
  "irr.sale_price": "Precio de venta",
  "irr.net_sale_proceeds": "Venta neta",
  "irr.capital_gains_tax": "IRPF de la ganancia",
  "sale_costs.notary": "Notaría de la venta",
  "offer.price": "Precio",
  "search.stressed_cashflow": "Cash flow con subida de tipos",
  "assumption.mortgage_rate": "Tipo de una hipoteca fija nueva",
  "assumption.rate_shock": "Subida de tipos del estrés",
  "assumption.cadastral_value": "Valor catastral estimado",
  "assumption.cadastral_land_value": "Valor catastral del suelo estimado",
  "assumption.construction_value": "Valor de la construcción estimado",
  "assumption.community_fees_monthly": "Comunidad al mes",
  "assumption.insurance_annual": "Seguro de hogar al año",
  "assumption.maintenance_annual": "Mantenimiento al año",
  "sale_costs.municipal_gains_tax": "Plusvalía municipal",
  "plan.low_rent_cashflow": "Cash flow con la renta baja de la zona",
  "assumption.variable_initial_rate": "Primer año de la variable",
  "assumption.variable_spread": "Diferencial de la variable",
  "mortgage_comparison.fija.first_payment": "Fija: primera cuota",
  "mortgage_comparison.fija.expected_total_interest": "Fija: intereses esperados",
  "mortgage_comparison.fija.stressed_max_payment": "Fija: cuota más alta en estrés",
  "mortgage_comparison.variable.first_payment": "Variable: primera cuota",
  "mortgage_comparison.variable.expected_total_interest": "Variable: intereses esperados",
  "mortgage_comparison.variable.stressed_max_payment": "Variable: cuota más alta en estrés",
};

export function label(key: string): string {
  return LABELS[key] ?? key;
}

/**
 * Número escrito por una persona en España → texto para la API, sin floats.
 * "189.500" y "1.290.109,45" llevan puntos de miles; "85,5" lleva coma decimal; "1290109.45" es
 * como lo devuelve la API.
 */
export function spanishNumber(text: string): string | null {
  const clean = text.trim().replace(/\s/g, "");
  if (/^\d{1,3}(\.\d{3})+(,\d+)?$/.test(clean)) return clean.replace(/\./g, "").replace(",", ".");
  return amount(clean);
}

/** Campos de un anuncio pegado (F4.1), en el orden en que se confirman. */
export const LISTING_LABELS: Record<string, string> = {
  price: "Precio",
  built_area_m2: "Superficie construida (m²)",
  usable_area_m2: "Superficie útil (m²)",
  rooms: "Habitaciones",
  bathrooms: "Baños",
  floor: "Planta",
  condition: "Estado",
  address: "Dirección",
  municipality: "Municipio",
  cadastral_ref: "Referencia catastral",
  year_built: "Año de construcción",
  community_fees: "Comunidad al mes (€)",
};

export const ORIGIN: Record<string, string> = {
  extraido: "del anuncio",
  corregido: "corregido por ti",
  usuario: "añadido por ti",
};

/** Campos de un lote de un anuncio del BOE (F4.4). */
export const LOT_LABELS: Record<string, string> = {
  label: "Lote",
  address: "Dirección",
  municipality: "Municipio",
  province: "Provincia",
  floor: "Planta",
  cadastral_ref: "Referencia catastral",
  built_area_m2: "Superficie (m²)",
  price: "Tipo de licitación",
  deposit: "Garantía",
};

export const PROPERTY_TYPE: Record<string, string> = {
  vivienda: "Vivienda",
  local: "Local",
  oficina: "Oficina",
  garaje: "Garaje",
  trastero: "Trastero",
  edificio: "Edificio",
  suelo: "Suelo",
  rustica: "Finca rústica",
  otro: "Otro",
};

export const ANNOUNCEMENT_STATUS: Record<string, string> = {
  pendiente: "Sin extraer",
  extraida: "Extraído, sin confirmar",
  confirmada: "Confirmado",
  no_aplica: "Sin lotes",
};
