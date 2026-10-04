import { useEffect, useRef, useState } from "react";
import { AssetsSection } from "./components/AssetsSection";
import { BooksSection } from "./components/BooksSection";
import { PeopleSection } from "./components/PeopleSection";
import { WeightSection } from "./components/WeightSection";
import {
  type Book,
  type MonthEntry,
  type Store,
  currentMonthKey,
  dividendThrough,
  emptyMonth,
  isMonthEmpty,
  monthHasMark,
  monthLabel,
  parseKey,
  shiftMonth,
  sumKeys,
  toKey,
  yearSeries,
} from "./model";
import { loadStore, parseStore, saveStore, storeFileName } from "./storage";

export function App() {
  const [store, setStore] = useState<Store>(loadStore);
  const [month, setMonth] = useState(() => {
    const parsed = parseKey(window.location.hash.replace("#", ""));
    return parsed ? toKey(parsed.year, parsed.month) : currentMonthKey();
  });
  const [message, setMessage] = useState("");
  const [importError, setImportError] = useState("");
  const [pendingImport, setPendingImport] = useState<Store | null>(null);
  const dirty = useRef(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!dirty.current) return;
    setMessage(saveStore(store) ? "이 브라우저에 저장했습니다." : "저장하지 못했습니다. 브라우저 저장 공간을 확인해 주세요.");
  }, [store]);

  useEffect(() => {
    const hash = `#${month}`;
    if (window.location.hash !== hash) history.replaceState(null, "", hash);
    document.title = `${monthLabel(month)} · 한달`;
  }, [month]);

  useEffect(() => {
    const onHash = () => {
      const parsed = parseKey(window.location.hash.replace("#", ""));
      if (parsed) setMonth(toKey(parsed.year, parsed.month));
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  function commit(recipe: (current: Store) => Store) {
    dirty.current = true;
    setStore(recipe);
  }

  function patchMonth(recipe: (entry: MonthEntry) => MonthEntry) {
    commit((current) => {
      const entry = recipe(current.months[month] ?? emptyMonth());
      const months = { ...current.months };
      if (isMonthEmpty(entry)) delete months[month];
      else months[month] = entry;
      return { ...current, months };
    });
  }

  const entry = store.months[month] ?? emptyMonth();
  const parsed = parseKey(month) ?? { year: new Date().getFullYear(), month: 1 };
  const previous = store.months[shiftMonth(month, -1)];
  const recorded = Array.from({ length: 12 }, (_, index) =>
    monthHasMark(store, toKey(parsed.year, index + 1)),
  ).filter(Boolean).length;

  function exportFile() {
    const blob = new Blob([JSON.stringify(store, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = storeFileName();
    link.click();
    URL.revokeObjectURL(url);
  }

  async function readFile(file: File) {
    try {
      const next = parseStore(JSON.parse(await file.text()));
      if (!next) {
        setPendingImport(null);
        setImportError("이 파일은 한달 기록이 아닙니다.");
        return;
      }
      setImportError("");
      setPendingImport(next);
    } catch {
      setPendingImport(null);
      setImportError("파일을 읽지 못했습니다.");
    }
  }

  return (
    <div className="sheet">
      <header className="mast">
        <p className="kicker">
          <i aria-hidden="true" />
          한달
        </p>
        <div className="monthline">
          <button type="button" className="navbtn" aria-label="이전 달" onClick={() => setMonth(shiftMonth(month, -1))}>
            <span aria-hidden="true">←</span>
          </button>
          <div className="monthtitle">
            <p className="yearlabel">{parsed.year}년</p>
            <h1>{parsed.month}월</h1>
          </div>
          <button type="button" className="navbtn" aria-label="다음 달" onClick={() => setMonth(shiftMonth(month, 1))}>
            <span aria-hidden="true">→</span>
          </button>
        </div>
        <p className="lede">자산, 책, 몸, 그리고 사람. 한 달에 한 번이면 됩니다.</p>
        <nav className="rail" aria-label={`${parsed.year}년`}>
          {Array.from({ length: 12 }, (_, index) => {
            const key = toKey(parsed.year, index + 1);
            const filled = monthHasMark(store, key);
            const current = key === month;
            return (
              <button
                key={key}
                type="button"
                aria-current={current ? "page" : undefined}
                aria-label={`${monthLabel(key)}${filled ? ", 기록 있음" : ""}`}
                data-filled={filled ? "true" : "false"}
                onClick={() => setMonth(key)}
              >
                {index + 1}
              </button>
            );
          })}
        </nav>
        {recorded > 0 ? (
          <p className="recorded">
            {parsed.year}년에 {recorded}개월을 적었습니다
          </p>
        ) : null}
        {previous?.next.trim() ? (
          <p className="recall">
            <span>지난달에 해두기로 한 것</span>
            {previous.next}
          </p>
        ) : null}
      </header>

      <nav className="jump" aria-label="구역">
        {(
          [
            ["assets", "자산"],
            ["books", "독서"],
            ["weight", "체중"],
            ["people", "사람"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })}
          >
            {label}
          </button>
        ))}
      </nav>

      <main>
        <div className="sentence">
          <label htmlFor="month-line">이번 달을 한 문장으로</label>
          <input
            id="month-line"
            maxLength={280}
            placeholder="나중에 이 달을 떠올릴 한 문장"
            value={entry.line}
            onChange={(event) => patchMonth((current) => ({ ...current, line: event.target.value }))}
          />
        </div>

        <AssetsSection
          month={month}
          year={parsed.year}
          assets={entry.assets}
          previous={previous?.assets ?? null}
          dividendWon={dividendThrough(store, month)}
          series={yearSeries(store, parsed.year, (item) =>
            sumKeys(item.assets, [
              "pensionIndex",
              "pensionSemi",
              "tossDividendStock",
              "tossSingle",
              "tossIndex",
              "isaIndex",
              "isaSemi",
            ]),
          )}
          onChange={(assets) => patchMonth((current) => ({ ...current, assets }))}
        />

        <BooksSection
          year={parsed.year}
          month={month}
          goal={store.bookGoal}
          books={store.books}
          onGoal={(bookGoal) => commit((current) => ({ ...current, bookGoal }))}
          onAdd={(title, author) =>
            commit((current) => ({
              ...current,
              books: [
                ...current.books,
                { id: crypto.randomUUID(), title, author, status: "reading", finishedMonth: null },
              ],
            }))
          }
          onUpdate={(id, patch) =>
            commit((current) => ({
              ...current,
              books: current.books.map((book) => (book.id === id ? ({ ...book, ...patch } as Book) : book)),
            }))
          }
          onDelete={(id) =>
            commit((current) => ({
              ...current,
              books: current.books.filter((book) => book.id !== id),
            }))
          }
        />

        <WeightSection
          month={month}
          year={parsed.year}
          weight={entry.weight}
          previous={previous?.weight ?? null}
          series={yearSeries(store, parsed.year, (item) => item.weight)}
          onChange={(weight) => patchMonth((current) => ({ ...current, weight }))}
        />

        <PeopleSection
          month={month}
          people={entry.people}
          previousReach={previous?.people.reach ?? ""}
          onChange={(people) => patchMonth((current) => ({ ...current, people }))}
        />

        <section className="closing" aria-labelledby="next-title">
          <h2 id="next-title">다음 달에 하나만</h2>
          <p>거창하지 않은 것. 다음 달 첫 화면에 다시 보입니다.</p>
          <input
            id="month-next"
            maxLength={160}
            aria-label="다음 달에 하나만"
            placeholder="다음 달에 지키면 되는 한 가지"
            value={entry.next}
            onChange={(event) => patchMonth((current) => ({ ...current, next: event.target.value }))}
          />
        </section>
      </main>

      <footer>
        <p>기록은 이 브라우저에만 있습니다. 다른 기기에서 이어 보려면 내보내 두세요.</p>
        <div className="footer-actions noprint">
          <button type="button" className="btn ghost" onClick={exportFile}>
            기록 내보내기
          </button>
          <button type="button" className="btn ghost" onClick={() => fileRef.current?.click()}>
            기록 가져오기
          </button>
          <input
            ref={fileRef}
            className="file"
            type="file"
            accept="application/json,.json"
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) void readFile(file);
            }}
          />
        </div>
        {importError ? (
          <p className="warn" role="alert">
            {importError}
          </p>
        ) : null}
        {pendingImport ? (
          <div className="confirm">
            <p>
              기록 {Object.keys(pendingImport.months).length}개월, 책 {pendingImport.books.length}권으로 바꿉니다. 이
              브라우저에 있던 기록은 사라집니다.
            </p>
            <div className="footer-actions">
              <button
                type="button"
                className="btn"
                onClick={() => {
                  const next = pendingImport;
                  setPendingImport(null);
                  commit(() => next);
                  setMessage("기록을 불러왔습니다.");
                }}
              >
                불러오기
              </button>
              <button type="button" className="btn ghost" onClick={() => setPendingImport(null)}>
                취소
              </button>
            </div>
          </div>
        ) : null}
        <p className="status" role="status">
          {message}
        </p>
      </footer>
    </div>
  );
}
