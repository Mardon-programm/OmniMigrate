import { Loader2 } from "lucide-react";

interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

const SIZES = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
  lg: "h-10 w-10",
};

export function Spinner({ size = "md", label, className = "" }: SpinnerProps) {
  return (
    <div className={`flex items-center gap-3 text-muted ${className}`} role="status">
      <Loader2 className={`animate-spin ${SIZES[size]}`} />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}
