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
        className={`inline-flex items-center gap-2 text-muted ${className}`}
      >
        <span className="relative flex h-2 w-8 overflow-hidden rounded-full bg-border">
          <span className="pipeline-bar-fill" />
        </span>
        {label && <span className="text-xs">{label}</span>}
      </span>
    );
  }

  const width = size === "lg" ? "w-56" : "w-36";
  return (
    <div
      role="status"
      className={`flex flex-col items-center gap-3 text-muted ${className}`}
    >
      <span className={`relative ${width}`}>
        <span className="pipeline-bar block">
          <span className="pipeline-bar-fill" />
          <span
            className="pipeline-bar-fill"
            style={{ animationDelay: "0.4s" }}
          />
        </span>
      </span>
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}
