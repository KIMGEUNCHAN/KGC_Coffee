import {
  type Assets,
  type Book,
  type MonthEntry,
  type People,
  type Store,
  BALANCE_KEYS,
  emptyAssets,
  emptyPeople,
  emptyStore,
  isMonthEmpty,
  parseKey,
} from "./model";

const KEY = "hangdal.v1";

function text(value: unknown, max: number): string {
  return typeof value === "string" ? value.slice(0, max) : "";
}

function won(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) return null;
  return value;
}

function weight(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 500) return null;
  return Math.round(value * 10) / 10;
}

function assetsOf(value: unknown): Assets {
  const assets = emptyAssets();
  if (!value || typeof value !== "object") return assets;
  const raw = value as Record<string, unknown>;
  for (const key of BALANCE_KEYS) assets[key] = won(raw[key]);
  assets.tossDividendIncome = won(raw.tossDividendIncome);
  return assets;
}

function peopleOf(value: unknown): People {
  const people = emptyPeople();
  if (!value || typeof value !== "object") return people;
  const raw = value as Record<string, unknown>;
  people.grateful = text(raw.grateful, 400);
  people.distant = text(raw.distant, 400);
  people.reach = text(raw.reach, 400);
  people.note = text(raw.note, 800);
  return people;
}

function monthOf(value: unknown): MonthEntry {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    line: text(raw.line, 280),
    next: text(raw.next, 160),
    weight: weight(raw.weight),
    assets: assetsOf(raw.assets),
    people: peopleOf(raw.people),
  };
}

function bookOf(value: unknown): Book | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const title = text(raw.title, 120).trim();
  if (!title) return null;
  const status = raw.status === "done" ? "done" : "reading";
  const finished = typeof raw.finishedMonth === "string" ? raw.finishedMonth : null;
  const finishedMonth = finished && parseKey(finished) ? finished : null;
  const id = typeof raw.id === "string" && raw.id.trim() ? raw.id.slice(0, 80) : crypto.randomUUID();
  return {
    id,
    title,
    author: text(raw.author, 80).trim(),
    status,
    finishedMonth: status === "done" ? finishedMonth : null,
  };
}

export function parseStore(value: unknown): Store | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  if (raw.version !== 1) return null;

  const goal = raw.bookGoal;
  const bookGoal =
    typeof goal === "number" && Number.isInteger(goal) && goal >= 1 && goal <= 100 ? goal : 12;

  const months: Store["months"] = {};
  if (raw.months && typeof raw.months === "object") {
    for (const [key, entry] of Object.entries(raw.months as Record<string, unknown>)) {
      if (!parseKey(key)) continue;
      const month = monthOf(entry);
      if (!isMonthEmpty(month)) months[key] = month;
    }
  }

  const books: Book[] = [];
  const seen = new Set<string>();
  if (Array.isArray(raw.books)) {
    for (const item of raw.books) {
      const book = bookOf(item);
      if (!book) continue;
      if (seen.has(book.id)) book.id = crypto.randomUUID();
      seen.add(book.id);
      books.push(book);
    }
  }

  return { version: 1, bookGoal, months, books };
}

export function loadStore(): Store {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return emptyStore();
    return parseStore(JSON.parse(raw)) ?? emptyStore();
  } catch {
    return emptyStore();
  }
}

export function saveStore(store: Store): boolean {
  try {
    localStorage.setItem(KEY, JSON.stringify(store));
    return true;
  } catch {
    return false;
  }
}

export function storeFileName(now = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `hangdal-${now.getFullYear()}-${month}-${day}.json`;
}
