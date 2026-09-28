interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

export function Spinner({ size = "md", label, className = "" }: SpinnerProps) {
  if (size === "sm") {
    return (
      <span
        role="status"
        aria-label={label}
        className={`inline-flex items-center gap-2 text-text-tertiary ${className}`}
      >
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-border-primary border-t-brand-emerald" />
        {label && <span className="text-caption">{label}</span>}
      </span>
    );
  }

  const dimension = size === "lg" ? "h-10 w-10" : "h-6 w-6";
  return (
    <div
      role="status"
      aria-label={label}
      className={`flex flex-col items-center gap-3 ${className}`}
    >
      <span
        className={`${dimension} animate-spin rounded-full border-3 border-border-primary border-t-brand-emerald`}
      />
      {label && <span className="text-body-sm text-text-tertiary">{label}</span>}
    </div>
  );
}