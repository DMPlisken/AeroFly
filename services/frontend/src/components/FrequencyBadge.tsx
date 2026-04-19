import type { FrequencyType } from "@/api/aerodromes";

export function FrequencyBadge({
  type,
  value,
}: {
  type: FrequencyType;
  value: string | number;
}) {
  return (
    <span className={`freq-badge freq-${type}`}>
      <span className="freq-type">{type.toUpperCase()}</span>
      <span className="freq-value">{value}</span>
    </span>
  );
}
