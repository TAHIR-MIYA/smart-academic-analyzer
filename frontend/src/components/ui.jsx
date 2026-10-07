import { AlertTriangle, CheckCircle2, Info, Loader2 } from "lucide-react";
import { classMeta } from "../lib/classes.js";
import { formatPercent } from "../lib/format.js";

export function PageHeader({ title, children, actions }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-5">
      <div className="min-w-0 max-w-2xl">
        <h1 className="break-words text-3xl font-semibold tracking-tight">{title}</h1>
        {children && <p className="mt-2 text-ink-muted">{children}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

const NOTICE_STYLES = {
  error: { box: "border-alert bg-alert-tint", icon: AlertTriangle, color: "text-alert" },
  warning: { box: "border-mark bg-mark-tint", icon: AlertTriangle, color: "text-[#8a6410]" },
  info: { box: "border-brand bg-brand-tint", icon: Info, color: "text-brand-dark" },
};

export function Notice({ kind = "info", title, children }) {
  const s = NOTICE_STYLES[kind];
  const Icon = s.icon;
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`flex gap-3 border-l-4 px-4 py-3 ${s.box}`}>
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${s.color}`} aria-hidden="true" />
      <div className="min-w-0 text-sm">
        {title && <p className="font-semibold">{title}</p>}
        <div className={title ? "mt-0.5" : ""}>{children}</div>
      </div>
    </div>
  );
}

export function Spinner({ label }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-ink-muted" role="status">
      <Loader2 className="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" />
      {label}
    </span>
  );
}

export function ProgressBar({ value, label }) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
      className="h-1.5 w-full overflow-hidden rounded-sm bg-rule"
    >
      <div className="h-full bg-brand transition-[width] duration-150 motion-reduce:transition-none" style={{ width: `${value}%` }} />
    </div>
  );
}

/** The document class as a catalogue mark: a coloured spine and the class name. */
export function ClassMark({ label, confidence, uncertain }) {
  const meta = classMeta(label);
  return (
    <span className="inline-flex items-stretch gap-2">
      <span className="w-1 rounded-sm" style={{ background: meta.color }} aria-hidden="true" />
      <span className="font-serif text-base font-semibold leading-tight" style={{ color: meta.color }}>
        {meta.name}
      </span>
      {confidence != null && (
        <span className="self-center text-xs text-ink-muted">
          {formatPercent(confidence)} sure{uncertain ? ", uncertain" : ""}
        </span>
      )}
    </span>
  );
}

export function StatusBadge({ done, doneText = "Analysed", todoText = "Not analysed" }) {
  return done ? (
    <span className="inline-flex items-center gap-1 text-sm text-brand-dark">
      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
      {doneText}
    </span>
  ) : (
    <span className="text-sm text-ink-muted">{todoText}</span>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="border border-dashed border-rule bg-paper-raised px-6 py-10 text-center">
      <h2 className="text-xl font-semibold">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-ink-muted">{children}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Section({ title, hint, children }) {
  return (
    <section className="mb-10">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2 border-b border-rule pb-2">
        <h2 className="text-xl font-semibold">{title}</h2>
        {hint && <p className="max-w-lg text-sm text-ink-muted">{hint}</p>}
      </div>
      {children}
    </section>
  );
}

/** Figures in one ruled row instead of a grid of cards. */
export function StatRow({ stats }) {
  return (
    <dl className="mb-10 grid grid-cols-2 divide-rule border-y border-rule sm:grid-cols-4 sm:divide-x">
      {stats.map((s) => (
        <div key={s.label} className="px-4 py-4 first:pl-0">
          <dt className="text-sm text-ink-muted">{s.label}</dt>
          <dd className="mt-1 font-serif text-3xl font-semibold">{s.value}</dd>
          {s.note && <dd className="mt-0.5 text-xs text-ink-muted">{s.note}</dd>}
        </div>
      ))}
    </dl>
  );
}

export const buttonClass = {
  primary:
    "inline-flex items-center gap-2 rounded bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-50",
  secondary:
    "inline-flex items-center gap-2 rounded border border-rule bg-paper-raised px-4 py-2 text-sm font-medium text-ink hover:border-ink-muted disabled:cursor-not-allowed disabled:opacity-50",
  danger:
    "inline-flex items-center gap-1 rounded border border-alert px-3 py-1 text-sm font-medium text-alert hover:bg-alert-tint disabled:opacity-50",
};
