// =============================================================================
// VeriField Nexus — Trust Badge Component
// =============================================================================
// Color-coded badge showing trust score status.
// =============================================================================

interface TrustBadgeProps {
  score: number | null;
  showScore?: boolean;
  size?: "sm" | "md" | "lg";
}

export default function TrustBadge({
  score,
  showScore = true,
  size = "md",
}: TrustBadgeProps) {
  // Determine status and colors from score
  let status = "Pending";
  let bgColor = "bg-slate-500/15";
  let textColor = "text-[var(--color-text-secondary)]";

  if (score !== null) {
    if (score >= 80) {
      status = "Verified";
      bgColor = "bg-emerald-500/15";
      textColor = "text-emerald-400";
    } else if (score >= 50) {
      status = "Review";
      bgColor = "bg-amber-500/15";
      textColor = "text-amber-400";
    } else {
      status = "Flagged";
      bgColor = "bg-red-500/15";
      textColor = "text-red-400";
    }
  }

  const sizeClasses = {
    sm: "text-[10px] px-2 py-0.5",
    md: "text-xs px-2.5 py-1",
    lg: "text-sm px-3 py-1.5",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold tracking-wide
        ${bgColor} ${textColor} ${sizeClasses[size]}`}
    >
      {showScore && score !== null && (
        <span className="font-bold">{Math.round(score)}</span>
      )}
      <span className="uppercase">{status}</span>
    </span>
  );
}
