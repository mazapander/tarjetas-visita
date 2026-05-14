import type { PropsWithChildren, ReactNode } from "react";

interface PanelProps extends PropsWithChildren {
  title?: string;
  eyebrow?: string;
  actions?: ReactNode;
  className?: string;
}

export function Panel({ title, eyebrow, actions, className, children }: PanelProps) {
  return (
    <section className={`panel ${className ?? ""}`.trim()}>
      {(title || actions) && (
        <header className="panel-header">
          <div>
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            {title ? <h2>{title}</h2> : null}
          </div>
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}
