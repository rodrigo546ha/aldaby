import type { ReactNode } from "react";

// Markdown mínimo para los textos legales (ADR-0039): títulos, párrafos, listas, citas, tablas,
// negrita y código. Sin HTML incrustado: todo se pinta como texto de React.

function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const pattern = /\*\*(.+?)\*\*|`(.+?)`/g;
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    const at = match.index ?? 0;
    if (at > last) parts.push(text.slice(last, at));
    parts.push(match[1] !== undefined ? <strong key={at}>{match[1]}</strong> : <code key={at}>{match[2]}</code>);
    last = at + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function cells(row: string): string[] {
  return row.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
}

function blocks(lines: string[]): ReactNode[] {
  const out: ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i += 1;
    } else if (line.startsWith("## ")) {
      out.push(<h2 key={i}>{inline(line.slice(3))}</h2>);
      i += 1;
    } else if (line.startsWith("> ") || line === ">") {
      const quoted: string[] = [];
      while (i < lines.length && (lines[i].startsWith("> ") || lines[i] === ">")) {
        quoted.push(lines[i].slice(2));
        i += 1;
      }
      out.push(<blockquote key={i}>{blocks(quoted)}</blockquote>);
    } else if (line.startsWith("|")) {
      const rows: string[][] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        if (!/^\|[\s|:-]+\|$/.test(lines[i].trim())) rows.push(cells(lines[i]));
        i += 1;
      }
      const [head, ...body] = rows;
      out.push(
        <table key={i}>
          <thead><tr>{head.map((c, j) => <th key={j} scope="col">{inline(c)}</th>)}</tr></thead>
          <tbody>
            {body.map((r, k) => <tr key={k}>{r.map((c, j) => <td key={j}>{inline(c)}</td>)}</tr>)}
          </tbody>
        </table>,
      );
    } else if (/^\s*- /.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*- /.test(lines[i])) {
        let item = lines[i].replace(/^\s*- /, "");
        i += 1;
        // Continuación de la línea (sangrada, sin guion)
        while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*- /.test(lines[i])) {
          item += ` ${lines[i].trim()}`;
          i += 1;
        }
        items.push(item);
      }
      out.push(<ul key={i}>{items.map((t, j) => <li key={j}>{inline(t)}</li>)}</ul>);
    } else {
      const paragraph: string[] = [];
      while (i < lines.length && lines[i].trim() && !/^(## |> |\||\s*- )/.test(lines[i])) {
        paragraph.push(lines[i].trim());
        i += 1;
      }
      out.push(<p key={i}>{inline(paragraph.join(" "))}</p>);
    }
  }
  return out;
}

export function Markdown({ text }: { text: string }) {
  return <div className="legal-text">{blocks(text.split("\n"))}</div>;
}
