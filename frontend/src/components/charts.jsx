import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const AXIS = { fontSize: 12, fill: "#586175" };

/** Every chart ships with a real table for screen readers (and for anyone who prefers exact numbers). */
function ChartTable({ caption, columns, rows }) {
  return (
    <table className="sr-only">
      <caption>{caption}</caption>
      <thead>
        <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>{r.map((cell, j) => <td key={j}>{cell}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}

/**
 * Bar chart. data: [{ name, <seriesKey>: number, color? }]; series: [{ key, name, color }].
 * horizontal=true draws horizontal bars (best for long labels); false draws columns.
 * A per-row `color` is used when there is a single series (e.g. one colour per document class).
 */
export function BarsChart({ data, series, horizontal = true, height, caption, tableCaption, categoryWidth = 120, format = (v) => v, tickInterval = 0 }) {
  const many = series.length > 1;
  const h = height ?? (horizontal ? Math.max(150, data.length * (many ? 54 : 32) + 44) : 260);
  const perRowColour = !many && data.some((d) => d.color);
  return (
    <figure>
      <div aria-hidden="true">
        <ResponsiveContainer width="100%" height={h}>
          <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ top: 4, right: 24, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#e4e7ee" horizontal={!horizontal} vertical={horizontal} />
            {horizontal ? (
              <>
                <XAxis type="number" tick={AXIS} tickFormatter={format} />
                <YAxis type="category" dataKey="name" width={categoryWidth} tickLine={false} axisLine={false} tick={{ ...AXIS, fill: "#17233b", fontSize: 13 }} interval={0} />
              </>
            ) : (
              <>
                <XAxis dataKey="name" tick={AXIS} interval={tickInterval} />
                <YAxis type="number" tick={AXIS} tickFormatter={format} allowDecimals={false} />
              </>
            )}
            <Tooltip cursor={{ fill: "#e9ecf1" }} formatter={(v) => format(v)} />
            {many && <Legend />}
            {series.map((s) => (
              <Bar key={s.key} dataKey={s.key} name={s.name} fill={s.color} barSize={many ? 14 : horizontal ? 18 : undefined} isAnimationActive={false} radius={horizontal ? [0, 3, 3, 0] : [3, 3, 0, 0]}>
                {perRowColour && data.map((d, i) => <Cell key={i} fill={d.color ?? s.color} />)}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ChartTable caption={tableCaption ?? caption} columns={["Item", ...series.map((s) => s.name)]} rows={data.map((d) => [d.name, ...series.map((s) => format(d[s.key]))])} />
      {caption && <figcaption className="mt-1 text-sm text-ink-muted">{caption}</figcaption>}
    </figure>
  );
}

/** Rank-frequency plot on log-log axes (Zipf's law: a straight falling line for natural text). */
export function ZipfChart({ points, caption }) {
  return (
    <figure>
      <div aria-hidden="true">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={points} margin={{ top: 8, right: 24, bottom: 20, left: 4 }}>
            <CartesianGrid stroke="#e4e7ee" />
            <XAxis dataKey="rank" type="number" scale="log" domain={[1, "dataMax"]} ticks={[1, 2, 5, 10, 30]} tick={AXIS} label={{ value: "Rank of word (log scale)", position: "bottom", offset: 2, fontSize: 12, fill: "#586175" }} />
            <YAxis type="number" scale="log" domain={[1, "dataMax"]} allowDataOverflow tick={AXIS} />
            <Tooltip formatter={(v) => [v, "Occurrences"]} labelFormatter={(r) => `Rank ${r}`} />
            <Line type="monotone" dataKey="count" stroke="#1f6f5c" strokeWidth={2} dot={{ r: 2.5 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <ChartTable caption="Most frequent words by rank" columns={["Rank", "Word", "Occurrences"]} rows={points.map((p) => [p.rank, p.word, p.count])} />
      {caption && <figcaption className="mt-1 text-sm text-ink-muted">{caption}</figcaption>}
    </figure>
  );
}

/** Confusion matrix as a real table; cell shading shows how many documents fall in each cell. */
export function ConfusionMatrix({ matrix, labels, names, accent = "#1e3a8a" }) {
  const max = Math.max(1, ...matrix.flat());
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-center text-sm">
        <caption className="mb-2 text-left text-sm text-ink-muted">Rows are the true class, columns the predicted class.</caption>
        <thead>
          <tr>
            <th scope="col" className="p-2" />
            {labels.map((l) => (
              <th key={l} scope="col" className="min-w-[5.5rem] px-2 py-2 font-medium">{names[l]}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={labels[i]}>
              <th scope="row" className="px-2 py-2 text-left font-medium">{names[labels[i]]}</th>
              {row.map((value, j) => {
                const strength = value / max;
                return (
                  <td
                    key={j}
                    className="border border-white tabular-nums"
                    style={{ background: value === 0 ? "#f0f2f6" : `color-mix(in srgb, ${accent} ${Math.round(18 + strength * 82)}%, white)`, color: strength > 0.45 ? "#fff" : "#17233b", fontWeight: i === j ? 600 : 400 }}
                    aria-label={`${value} ${names[labels[i]]} documents predicted as ${names[labels[j]]}`}
                  >
                    {value}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
