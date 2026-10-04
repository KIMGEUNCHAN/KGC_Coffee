import type { SeriesPoint } from "../model";

export function Sparkline({
  points,
  activeKey,
  formatValue,
  label,
}: {
  points: SeriesPoint[];
  activeKey: string;
  formatValue: (value: number) => string;
  label: string;
}) {
  const known = points.filter((point) => point.value != null);
  if (known.length < 2) return null;

  const width = 640;
  const height = 78;
  const pad = 8;
  const values = known.map((point) => point.value as number);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  const coords = points.map((point, index) => {
    if (point.value == null) return null;
    const x = pad + (index * (width - pad * 2)) / Math.max(points.length - 1, 1);
    const y = pad + (1 - (point.value - min) / span) * (height - pad * 2);
    return { ...point, x, y, value: point.value };
  });

  const paths: string[] = [];
  let commands: string[] = [];
  for (const coord of coords) {
    if (!coord) {
      if (commands.length > 1) paths.push(commands.join(" "));
      commands = [];
      continue;
    }
    commands.push(`${commands.length === 0 ? "M" : "L"}${coord.x.toFixed(1)},${coord.y.toFixed(1)}`);
  }
  if (commands.length > 1) paths.push(commands.join(" "));

  const caption = known.map((point) => `${point.label} ${formatValue(point.value as number)}`).join(", ");

  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${label}. ${caption}`}>
        {paths.map((d) => (
          <path key={d} d={d} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        ))}
        {coords.map((coord) =>
          coord ? (
            <circle
              key={coord.key}
              cx={coord.x}
              cy={coord.y}
              r={coord.key === activeKey ? 5 : 3.5}
              className={coord.key === activeKey ? "dot active" : "dot"}
            >
              <title>
                {coord.label} {formatValue(coord.value)}
              </title>
            </circle>
          ) : null,
        )}
      </svg>
    </figure>
  );
}
