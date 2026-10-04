/** 평가액 입력(만원)을 원 단위 정수로 바꿉니다. 비어 있으면 null. */
export function parseMan(raw: string): number | null {
  const t = raw.replace(/,/g, "").trim();
  if (t === "") return null;
  if (!/^\d+(\.\d{0,4})?$/.test(t)) return null;
  const won = Math.round(Number(t) * 10_000);
  if (!Number.isSafeInteger(won)) return null;
  return won;
}

/** 원 단위 정수 입력. */
export function parseWon(raw: string): number | null {
  const t = raw.replace(/,/g, "").trim();
  if (t === "") return null;
  if (!/^\d+$/.test(t)) return null;
  const n = Number(t);
  if (!Number.isSafeInteger(n)) return null;
  return n;
}

/** 몸무게 kg. 소수 한 자리. */
export function parseKg(raw: string): number | null {
  const t = raw.replace(/,/g, "").trim();
  if (t === "") return null;
  if (!/^\d+(\.\d{0,1})?$/.test(t)) return null;
  const n = Number(t);
  if (!Number.isFinite(n) || n > 500) return null;
  return Math.round(n * 10) / 10;
}

export function formatManInput(won: number): string {
  const man = won / 10_000;
  return man.toLocaleString("ko-KR", { maximumFractionDigits: 4 });
}

export function formatWonInput(won: number): string {
  return Math.round(won).toLocaleString("ko-KR");
}

export function formatKgInput(kg: number): string {
  return kg.toLocaleString("ko-KR", { maximumFractionDigits: 1 });
}

export function formatWon(won: number): string {
  const sign = won < 0 ? "-" : "";
  const abs = Math.round(Math.abs(won));
  const eok = Math.floor(abs / 100_000_000);
  const man = Math.floor((abs % 100_000_000) / 10_000);
  const rest = abs % 10_000;
  const manText = man > 0 ? `${man.toLocaleString("ko-KR")}만` : "";
  const restText = rest > 0 ? rest.toLocaleString("ko-KR") : "";

  if (eok > 0) {
    const tail = [manText, restText].filter(Boolean).join(" ");
    return tail ? `${sign}${eok.toLocaleString("ko-KR")}억 ${tail}원` : `${sign}${eok.toLocaleString("ko-KR")}억원`;
  }
  if (man > 0) {
    return restText
      ? `${sign}${manText} ${restText}원`
      : `${sign}${manText}원`;
  }
  return `${sign}${rest.toLocaleString("ko-KR")}원`;
}

export function formatKg(kg: number): string {
  return `${kg.toLocaleString("ko-KR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}kg`;
}

export function moneyDeltaPhrase(deltaWon: number, partial: boolean): string {
  const scope = partial ? "양쪽에 모두 적은 항목만, " : "";
  if (deltaWon === 0) return `${scope}지난달과 같습니다`;
  const word = deltaWon > 0 ? "늘었습니다" : "줄었습니다";
  return `${scope}지난달보다 ${formatWon(Math.abs(deltaWon))} ${word}`;
}

export function weightDeltaPhrase(current: number, previous: number): string {
  const delta = Math.round((current - previous) * 10) / 10;
  if (delta === 0) return "지난달과 같습니다";
  const abs = Math.abs(delta).toLocaleString("ko-KR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  return delta < 0
    ? `지난달보다 ${abs}kg 줄었습니다`
    : `지난달보다 ${abs}kg 늘었습니다`;
}
