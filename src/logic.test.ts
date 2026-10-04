import { formatWon, moneyDeltaPhrase, parseKg, parseMan, parseWon, weightDeltaPhrase } from "./format";
import {
  compareBalances,
  dividendThrough,
  doneBooksInYear,
  emptyAssets,
  emptyMonth,
  emptyStore,
  isMonthEmpty,
  monthHasMark,
  shiftMonth,
  sleeveTotals,
  sumKeys,
} from "./model";
import { parseStore } from "./storage";

describe("금액", () => {
  it("만원 입력을 원으로 보관한다", () => {
    expect(parseMan("4,500")).toBe(45_000_000);
    expect(parseMan("4500.5")).toBe(45_005_000);
    expect(parseMan("")).toBeNull();
    expect(parseMan("-1")).toBeNull();
    expect(parseWon("87,000")).toBe(87_000);
    expect(parseWon("87.5")).toBeNull();
  });

  it("억과 만 단위로 보여 준다", () => {
    expect(formatWon(115_000_000)).toBe("1억 1,500만원");
    expect(formatWon(100_000_000)).toBe("1억원");
    expect(formatWon(87_000)).toBe("8만 7,000원");
    expect(formatWon(0)).toBe("0원");
  });

  it("평가액 합계에서 배당금은 뺀다", () => {
    const assets = {
      ...emptyAssets(),
      pensionIndex: 45_000_000,
      pensionSemi: 8_000_000,
      tossDividendStock: 12_000_000,
      tossSingle: 9_000_000,
      tossIndex: 15_000_000,
      tossDividendIncome: 87_000,
      isaIndex: 20_000_000,
      isaSemi: 6_000_000,
    };
    expect(
      sumKeys(assets, [
        "pensionIndex",
        "pensionSemi",
        "tossDividendStock",
        "tossSingle",
        "tossIndex",
        "isaIndex",
        "isaSemi",
      ]),
    ).toBe(115_000_000);
    expect(sleeveTotals(assets).find((sleeve) => sleeve.id === "semi")?.amount).toBe(14_000_000);
    expect(sleeveTotals(assets).find((sleeve) => sleeve.id === "index")?.amount).toBe(80_000_000);
  });

  it("양쪽에 있는 항목만 지난달과 비교한다", () => {
    const current = { ...emptyAssets(), pensionIndex: 100, pensionSemi: null };
    const previous = { ...emptyAssets(), pensionIndex: 80, pensionSemi: 10, tossDividendIncome: 50 };
    expect(compareBalances(current, previous)).toEqual({ delta: 20, partial: true });
    expect(moneyDeltaPhrase(20, true)).toContain("양쪽에 모두 적은 항목만");
    expect(compareBalances(emptyAssets(), emptyAssets())).toBeNull();
  });
});

describe("달과 몸무게", () => {
  it("해를 넘겨 이동한다", () => {
    expect(shiftMonth("2026-01", -1)).toBe("2025-12");
    expect(shiftMonth("2026-12", 1)).toBe("2027-01");
  });

  it("몸무게는 소수 한 자리만 받는다", () => {
    expect(parseKg("71.2")).toBe(71.2);
    expect(parseKg("71.")).toBe(71);
    expect(parseKg("71.25")).toBeNull();
    expect(parseKg("600")).toBeNull();
    expect(weightDeltaPhrase(71.2, 71.6)).toBe("지난달보다 0.4kg 줄었습니다");
  });

  it("빈 달은 기록으로 치지 않고, 그달에 다 읽은 책은 친다", () => {
    const store = emptyStore();
    expect(isMonthEmpty(emptyMonth())).toBe(true);
    expect(monthHasMark(store, "2026-10")).toBe(false);
    store.books.push({
      id: "1",
      title: "책",
      author: "",
      status: "done",
      finishedMonth: "2026-10",
    });
    expect(monthHasMark(store, "2026-10")).toBe(true);
    expect(doneBooksInYear(store.books, 2026)).toHaveLength(1);
    expect(doneBooksInYear(store.books, 2025)).toHaveLength(0);
  });

  it("배당금은 보고 있는 달까지만 더한다", () => {
    const store = emptyStore();
    const march = emptyMonth();
    march.assets.tossDividendIncome = 10_000;
    const october = emptyMonth();
    october.assets.tossDividendIncome = 20_000;
    store.months["2026-03"] = march;
    store.months["2026-10"] = october;
    expect(dividendThrough(store, "2026-03")).toBe(10_000);
    expect(dividendThrough(store, "2026-10")).toBe(30_000);
  });
});

describe("저장 파일", () => {
  it("버전이 다르거나 비어 있는 달은 걸러 낸다", () => {
    expect(parseStore({ version: 2 })).toBeNull();
    const store = parseStore({
      version: 1,
      bookGoal: 12,
      months: {
        "2026-10": emptyMonth(),
        "2026-09": {
          ...emptyMonth(),
          weight: 71.4,
          line: "  ",
        },
        "nope": { ...emptyMonth(), weight: 70 },
      },
      books: [
        { id: "a", title: "읽는 책", author: "누구", status: "reading", finishedMonth: "2026-10" },
        { id: "a", title: "끝낸 책", author: "", status: "done", finishedMonth: "2026-09" },
        { id: "b", title: "   ", author: "", status: "done", finishedMonth: "2026-09" },
      ],
    });
    expect(store).not.toBeNull();
    expect(store?.months["2026-10"]).toBeUndefined();
    expect(store?.months["2026-09"]?.weight).toBe(71.4);
    expect(store?.months.nope).toBeUndefined();
    expect(store?.books).toHaveLength(2);
    expect(store?.books[0]?.finishedMonth).toBeNull();
    expect(store?.books[1]?.id).not.toBe("a");
    expect(store?.books[1]?.finishedMonth).toBe("2026-09");
  });
});
