"use client";

import { useEffect, useId, useRef, useState } from "react";

import type { components } from "../lib/api-types";

type Municipality = components["schemas"]["MunicipalityOut"];

// Elegir un municipio por su nombre oficial del INE (ADR-0056), sin escribir su código. Patrón
// combobox de WAI-ARIA: flechas para moverse, Intro para elegir, Escape para cerrar.

export function MunicipalityPicker({
  id,
  value,
  onChange,
  invalid,
  describedBy,
}: {
  id: string;
  value: string; // territorio de las reglas: ES-13-28079
  onChange: (territory: string) => void;
  invalid?: boolean;
  describedBy?: string;
}) {
  const [text, setText] = useState("");
  const [options, setOptions] = useState<Municipality[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = useId();
  const typed = useRef(false);

  // El nombre del municipio ya elegido (también el del ejemplo)
  useEffect(() => {
    const code = value.split("-")[2];
    if (!code) return;
    fetch(`/api/territory/municipalities/${code}`)
      .then(async (resp) => {
        if (!resp.ok) return;
        const m = (await resp.json()) as Municipality;
        if (!typed.current) setText(`${m.name} (${m.province})`);
      })
      .catch(() => undefined);
  }, [value]);

  useEffect(() => {
    if (!typed.current || text.trim().length < 2) {
      setOptions([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      fetch(`/api/territory/municipalities?q=${encodeURIComponent(text.trim())}`, { signal: controller.signal })
        .then(async (resp) => (resp.ok ? setOptions((await resp.json()) as Municipality[]) : setOptions([])))
        .catch(() => undefined);
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [text]);

  function choose(m: Municipality) {
    typed.current = false;
    setText(`${m.name} (${m.province})`);
    setOpen(false);
    setOptions([]);
    onChange(m.territory);
  }

  const shown = open && options.length > 0;
  return (
    <div className="combobox">
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={shown}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={shown ? `${listId}-${active}` : undefined}
        aria-invalid={invalid || undefined}
        aria-describedby={describedBy}
        autoComplete="off"
        placeholder="Escribe el nombre: Getafe, Bilbao…"
        value={text}
        onChange={(e) => {
          typed.current = true;
          setText(e.target.value);
          setOpen(true);
          setActive(0);
          if (value) onChange("");
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" && options.length) {
            e.preventDefault();
            setOpen(true);
            setActive((a) => Math.min(a + 1, options.length - 1));
          } else if (e.key === "ArrowUp" && options.length) {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter" && shown) {
            e.preventDefault();
            choose(options[active]);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
      />
      {shown && (
        <ul id={listId} role="listbox" className="combobox-list">
          {options.map((m, i) => (
            <li
              key={m.code}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(m);
              }}
              onMouseEnter={() => setActive(i)}
            >
              <span>{m.name}</span>
              <span className="combobox-meta">{m.province}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
