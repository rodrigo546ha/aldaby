// Iconos de trazo (DESIGN.md): 24 × 24, trazo de 1,6 y extremos redondeados, en currentColor.
// Junto a un texto que dice lo mismo son decorativos (aria-hidden); solos, el botón lleva su nombre.

const PATHS = {
  back: <path d="M15 5 8 12l7 7" />,
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m20 20-4.2-4.2" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 7.6v.1" />
    </>
  ),
  warning: (
    <>
      <path d="M12 3.5 21.5 20h-19L12 3.5Z" />
      <path d="M12 10v4.5M12 17.4v.1" />
    </>
  ),
  danger: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m8.8 8.8 6.4 6.4M15.2 8.8l-6.4 6.4" />
    </>
  ),
  success: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12.3 2.8 2.7L16.2 9.5" />
    </>
  ),
  external: <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  dot: <circle cx="12" cy="12" r="3" fill="currentColor" stroke="none" />,
  pin: (
    <>
      <path d="M12 21s-6.5-5.4-6.5-11a6.5 6.5 0 0 1 13 0c0 5.6-6.5 11-6.5 11Z" />
      <circle cx="12" cy="10" r="2.4" />
    </>
  ),
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, small = false, label }: { name: IconName; small?: boolean; label?: string }) {
  return (
    <svg
      className={small ? "icon-sm" : "icon"}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      {PATHS[name]}
    </svg>
  );
}

/** Aviso del design system: un tono, su icono y una frase. */
export function Callout({
  tone,
  children,
}: {
  tone: "info" | "warning" | "danger" | "success";
  children: React.ReactNode;
}) {
  return (
    <div className={`callout ${tone}`} role={tone === "danger" ? "alert" : undefined}>
      <Icon name={tone} />
      <div>{children}</div>
    </div>
  );
}
