import { formatKg, weightDeltaPhrase } from "../format";
import type { SeriesPoint } from "../model";
import { NumericField } from "./NumericField";
import { SeriesNote, Sparkline } from "./Sparkline";

export function WeightSection({
  month,
  year,
  weight,
  previous,
  series,
  onChange,
}: {
  month: string;
  year: number;
  weight: number | null;
  previous: number | null;
  series: SeriesPoint[];
  onChange: (weight: number | null) => void;
}) {
  return (
    <section id="weight" aria-labelledby="weight-title">
      <header className="sec-h">
        <h2 id="weight-title">
          <span>03</span>체중
        </h2>
        <p>그달의 아침 몸무게 하나만 적습니다.</p>
      </header>
      <NumericField
        key={`${month}-weight`}
        id="weight"
        label="아침 몸무게"
        unit="kg"
        value={weight}
        aside={previous == null ? null : `지난달 ${formatKg(previous)}`}
        placeholder=""
        onChange={onChange}
      />
      {weight != null && previous != null ? <p className="delta flat">{weightDeltaPhrase(weight, previous)}</p> : null}
      <Sparkline points={series} activeKey={month} formatValue={formatKg} label={`${year}년 아침 몸무게`} />
      <SeriesNote year={year} points={series} formatValue={formatKg} />
    </section>
  );
}
