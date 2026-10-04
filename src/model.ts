export const BALANCE_KEYS = [
  "pensionIndex",
  "pensionSemi",
  "tossDividendStock",
  "tossSingle",
  "tossIndex",
  "isaIndex",
  "isaSemi",
] as const;

export type BalanceKey = (typeof BALANCE_KEYS)[number];

export type SleeveId = "index" | "semi" | "dividend" | "single";

export interface Assets {
  pensionIndex: number | null;
  pensionSemi: number | null;
  tossDividendStock: number | null;
  tossSingle: number | null;
  tossIndex: number | null;
  /** 이번 달 입금된 배당금(원). 평가액 합계에 넣지 않습니다. */
  tossDividendIncome: number | null;
  isaIndex: number | null;
  isaSemi: number | null;
}

export interface People {
  grateful: string;
  distant: string;
  reach: string;
  note: string;
}

export interface MonthEntry {
  line: string;
  next: string;
  weight: number | null;
  assets: Assets;
  people: People;
}

export interface Book {
  id: string;
  title: string;
  author: string;
  status: "reading" | "done";
  /** YYYY-MM. 다 읽은 책에만 있습니다. */
  finishedMonth: string | null;
}

export interface Store {
  version: 1;
  bookGoal: number;
  months: Record<string, MonthEntry>;
  books: Book[];
}

export interface SeriesPoint {
  key: string;
  label: string;
  value: number | null;
}

export interface AccountField {
  key: BalanceKey;
  label: string;
  sleeve: SleeveId;
}

export interface AccountDef {
  id: "pension" | "toss" | "isa";
  name: string;
  description: string;
  fields: AccountField[];
}

export const ACCOUNTS: AccountDef[] = [
  {
    id: "pension",
    name: "퇴직연금",
    description: "지수투자, 반도체",
    fields: [
      { key: "pensionIndex", label: "지수투자", sleeve: "index" },
      { key: "pensionSemi", label: "반도체", sleeve: "semi" },
    ],
  },
  {
    id: "toss",
    name: "토스증권",
    description: "배당주, 개별주, 지수투자",
    fields: [
      { key: "tossDividendStock", label: "배당주", sleeve: "dividend" },
      { key: "tossSingle", label: "개별주", sleeve: "single" },
      { key: "tossIndex", label: "지수투자", sleeve: "index" },
    ],
  },
  {
    id: "isa",
    name: "ISA",
    description: "지수투자, 반도체",
    fields: [
      { key: "isaIndex", label: "지수투자", sleeve: "index" },
      { key: "isaSemi", label: "반도체", sleeve: "semi" },
    ],
  },
];

export const SLEEVES: { id: SleeveId; label: string; keys: BalanceKey[] }[] = [
  { id: "index", label: "지수투자", keys: ["pensionIndex", "tossIndex", "isaIndex"] },
  { id: "semi", label: "반도체", keys: ["pensionSemi", "isaSemi"] },
  { id: "dividend", label: "배당주", keys: ["tossDividendStock"] },
  { id: "single", label: "개별주", keys: ["tossSingle"] },
];

export function emptyAssets(): Assets {
  return {
    pensionIndex: null,
    pensionSemi: null,
    tossDividendStock: null,
    tossSingle: null,
    tossIndex: null,
    tossDividendIncome: null,
    isaIndex: null,
    isaSemi: null,
  };
}

export function emptyPeople(): People {
  return { grateful: "", distant: "", reach: "", note: "" };
}

export function emptyMonth(): MonthEntry {
  return {
    line: "",
    next: "",
    weight: null,
    assets: emptyAssets(),
    people: emptyPeople(),
  };
}

export function emptyStore(): Store {
  return { version: 1, bookGoal: 12, months: {}, books: [] };
}

export function toKey(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}`;
}

export function parseKey(key: string): { year: number; month: number } | null {
  const match = /^(\d{4})-(\d{2})$/.exec(key);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  if (month < 1 || month > 12) return null;
  if (year < 2000 || year > 2100) return null;
  return { year, month };
}

export function currentMonthKey(now = new Date()): string {
  return toKey(now.getFullYear(), now.getMonth() + 1);
}

export function shiftMonth(key: string, delta: number): string {
  const parsed = parseKey(key) ?? { year: 2000, month: 1 };
  const date = new Date(parsed.year, parsed.month - 1 + delta, 1);
  return toKey(date.getFullYear(), date.getMonth() + 1);
}

export function monthLabel(key: string): string {
  const parsed = parseKey(key);
  if (!parsed) return key;
  return `${parsed.year}년 ${parsed.month}월`;
}

export function isMonthEmpty(entry: MonthEntry | undefined): boolean {
  if (!entry) return true;
  if (entry.line.trim() || entry.next.trim()) return false;
  if (entry.weight != null) return false;
  if (Object.values(entry.people).some((value) => value.trim())) return false;
  if (Object.values(entry.assets).some((value) => value != null)) return false;
  return true;
}

export function monthHasMark(store: Store, key: string): boolean {
  if (!isMonthEmpty(store.months[key])) return true;
  return store.books.some((book) => book.status === "done" && book.finishedMonth === key);
}

export function sumKeys(assets: Assets, keys: readonly BalanceKey[]): number | null {
  let sum = 0;
  let any = false;
  for (const key of keys) {
    const value = assets[key];
    if (value != null) {
      sum += value;
      any = true;
    }
  }
  return any ? sum : null;
}

export function balanceFilled(assets: Assets): number {
  return BALANCE_KEYS.filter((key) => assets[key] != null).length;
}

export function compareBalances(
  current: Assets,
  previous: Assets,
): { delta: number; partial: boolean } | null {
  let delta = 0;
  let any = false;
  let partial = false;
  for (const key of BALANCE_KEYS) {
    const left = current[key];
    const right = previous[key];
    if (left != null && right != null) {
      delta += left - right;
      any = true;
    } else if (left != null || right != null) {
      partial = true;
    }
  }
  if (!any) return null;
  return { delta, partial };
}

export interface SleeveTotal {
  id: SleeveId;
  label: string;
  amount: number | null;
}

export function sleeveTotals(assets: Assets): SleeveTotal[] {
  return SLEEVES.map((sleeve) => ({
    id: sleeve.id,
    label: sleeve.label,
    amount: sumKeys(assets, sleeve.keys),
  }));
}

export function yearSeries(
  store: Store,
  year: number,
  pick: (entry: MonthEntry) => number | null,
): SeriesPoint[] {
  return Array.from({ length: 12 }, (_, index) => {
    const key = toKey(year, index + 1);
    const entry = store.months[key];
    return { key, label: `${index + 1}월`, value: entry ? pick(entry) : null };
  });
}

export function dividendThrough(store: Store, monthKey: string): number {
  const parsed = parseKey(monthKey);
  if (!parsed) return 0;
  let sum = 0;
  for (let month = 1; month <= parsed.month; month += 1) {
    sum += store.months[toKey(parsed.year, month)]?.assets.tossDividendIncome ?? 0;
  }
  return sum;
}

export function doneBooksInYear(books: Book[], year: number): Book[] {
  return books.filter(
    (book) => book.status === "done" && book.finishedMonth?.startsWith(`${year}-`),
  );
}

export function readingBooks(books: Book[]): Book[] {
  return books.filter((book) => book.status === "reading");
}

export function endpoints(points: SeriesPoint[]): { start: SeriesPoint; end: SeriesPoint } | null {
  const known = points.filter((point) => point.value != null);
  if (known.length < 2) return null;
  return { start: known[0], end: known[known.length - 1] };
}
