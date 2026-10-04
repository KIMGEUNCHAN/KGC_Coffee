import { formatManInput, formatWon, moneyDeltaPhrase } from "../format";
import {
  ACCOUNTS,
  type Assets,
  type SeriesPoint,
  balanceFilled,
  compareBalances,
  sleeveTotals,
  sumKeys,
} from "../model";
import { NumericField } from "./NumericField";
import { Sparkline } from "./Sparkline";

export function AssetsSection({
  month,
  year,
  assets,
  previous,
  series,
  dividendWon,
  onChange,
}: {
  month: string;
  year: number;
  assets: Assets;
  previous: Assets | null;
  series: SeriesPoint[];
  dividendWon: number;
  onChange: (assets: Assets) => void;
}) {
  const total = sumKeys(assets, [
    "pensionIndex",
    "pensionSemi",
    "tossDividendStock",
    "tossSingle",
    "tossIndex",
    "isaIndex",
    "isaSemi",
  ]);
  const filled = balanceFilled(assets);
  const comparison = previous ? compareBalances(assets, previous) : null;
  const sleeves = sleeveTotals(assets).filter((sleeve) => sleeve.amount != null && sleeve.amount > 0);
  const sleeveSum = sleeves.reduce((sum, sleeve) => sum + (sleeve.amount ?? 0), 0);

  function aside(key: keyof Assets): string | null {
    const last = previous?.[key];
    if (last == null) return null;
    if (key === "tossDividendIncome") return `지난달 ${formatWon(last)}`;
    return `지난달 ${formatManInput(last)}만`;
  }

  return (
    <section id="assets" aria-labelledby="assets-title">
      <header className="sec-h">
        <h2 id="assets-title">
          <span>01</span>자산
        </h2>
        <p>평가액은 만원으로 적습니다. 이번 달 배당금은 합계에 넣지 않습니다.</p>
      </header>

      <div className="summary">
        <p className="total-label">{filled > 0 && filled < 7 ? "입력한 평가액 합계" : "평가액 합계"}</p>
        <p className="total-num">{total == null ? "—" : formatWon(total)}</p>
        {comparison ? (
          <p className="delta" data-sign={comparison.delta > 0 ? "up" : comparison.delta < 0 ? "down" : "flat"}>
            {moneyDeltaPhrase(comparison.delta, comparison.partial)}
          </p>
        ) : null}

        <div className="acctotals">
          {ACCOUNTS.map((account) => {
            const amount = sumKeys(
              assets,
              account.fields.map((field) => field.key),
            );
            return (
              <div key={account.id}>
                <span>{account.name}</span>
                <strong>{amount == null ? "—" : formatWon(amount)}</strong>
              </div>
            );
          })}
        </div>

        {sleeveSum > 0 ? (
          <>
            <div className="stack" aria-hidden="true">
              {sleeves.map((sleeve) => (
                <span
                  key={sleeve.id}
                  data-sleeve={sleeve.id}
                  style={{ width: `${((sleeve.amount ?? 0) / sleeveSum) * 100}%` }}
                  title={`${sleeve.label} ${formatWon(sleeve.amount ?? 0)}`}
                />
              ))}
            </div>
            <ul className="legend">
              {sleeves.map((sleeve) => (
                <li key={sleeve.id}>
                  <i data-sleeve={sleeve.id} />
                  <span>
                    {sleeve.label} {formatWon(sleeve.amount ?? 0)}
                    <em> {Math.round(((sleeve.amount ?? 0) / sleeveSum) * 100)}%</em>
                  </span>
                </li>
              ))}
            </ul>
          </>
        ) : null}

        <Sparkline points={series} activeKey={month} formatValue={formatWon} label={`${year}년 평가액`} />
      </div>

      {ACCOUNTS.map((account) => {
        const amount = sumKeys(
          assets,
          account.fields.map((field) => field.key),
        );
        return (
          <div className="account" key={account.id}>
            <header>
              <div>
                <h3>{account.name}</h3>
                <p>{account.description}</p>
              </div>
              <strong>{amount == null ? "" : formatWon(amount)}</strong>
            </header>
            {account.fields.map((field) => (
              <NumericField
                key={`${month}-${field.key}`}
                id={field.key}
                label={field.label}
                unit="man"
                value={assets[field.key]}
                aside={aside(field.key)}
                placeholder=""
                onChange={(value) => onChange({ ...assets, [field.key]: value })}
              />
            ))}
            {account.id === "toss" ? (
              <>
                <NumericField
                  key={`${month}-dividend`}
                  id="tossDividendIncome"
                  label="이번 달 배당금"
                  unit="won"
                  value={assets.tossDividendIncome}
                  aside={aside("tossDividendIncome")}
                  placeholder="없으면 비워 두기"
                  onChange={(value) => onChange({ ...assets, tossDividendIncome: value })}
                />
                {dividendWon > 0 ? (
                  <p className="ytd">
                    {year}년 {Number(month.slice(5))}월까지 받은 배당 {formatWon(dividendWon)}
                  </p>
                ) : null}
              </>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}
