import { useState } from "react";
import type { Book } from "../model";
import { monthLabel, parseKey } from "../model";

export function BooksSection({
  year,
  month,
  goal,
  books,
  onGoal,
  onAdd,
  onUpdate,
  onDelete,
}: {
  year: number;
  month: string;
  goal: number;
  books: Book[];
  onGoal: (goal: number) => void;
  onAdd: (title: string, author: string) => void;
  onUpdate: (id: string, patch: Partial<Book>) => void;
  onDelete: (id: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const done = books.filter((book) => book.status === "done" && book.finishedMonth?.startsWith(`${year}-`));
  const reading = books.filter((book) => book.status === "reading");
  const doneThisMonth = done.filter((book) => book.finishedMonth === month);
  const doneOther = done
    .filter((book) => book.finishedMonth !== month)
    .sort((a, b) => (a.finishedMonth ?? "").localeCompare(b.finishedMonth ?? ""));
  const ratio = Math.min(100, Math.round((done.length / goal) * 100));

  return (
    <section id="books" aria-labelledby="books-title">
      <header className="sec-h">
        <h2 id="books-title">
          <span>02</span>독서
        </h2>
        <p>다 읽은 책만 올해 목표에 들어갑니다.</p>
      </header>

      <div className="goalhead">
        <p className="goalcount">
          <strong>
            {done.length}
            <span> / {goal}</span>
          </strong>
          권
          {done.length > goal ? <em> 목표를 넘겼습니다</em> : null}
        </p>
        <label className="goaledit">
          매년 목표
          <input
            inputMode="numeric"
            aria-label="매년 읽을 책 목표"
            value={goal}
            onChange={(event) => {
              const next = Number(event.target.value.replace(/[^\d]/g, ""));
              if (Number.isInteger(next) && next >= 1 && next <= 100) onGoal(next);
            }}
          />
          권
        </label>
      </div>
      <div
        className="progress"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={goal}
        aria-valuenow={Math.min(done.length, goal)}
        aria-label={`${year}년 독서 ${done.length}권, 목표 ${goal}권`}
      >
        <span style={{ width: `${ratio}%` }} />
      </div>

      {doneThisMonth.length > 0 ? (
        <div className="bookgroup">
          <h3>이 달에 다 읽음</h3>
          {doneThisMonth.map((book) => (
            <BookRow
              key={book.id}
              book={book}
              year={year}
              month={month}
              pendingDelete={pendingDelete}
              onAskDelete={setPendingDelete}
              onUpdate={onUpdate}
              onDelete={onDelete}
            />
          ))}
        </div>
      ) : null}

      <div className="bookgroup">
        <h3>읽는 중</h3>
        {reading.length === 0 ? <p className="empty">읽는 중인 책이 없습니다.</p> : null}
        {reading.map((book) => (
          <BookRow
            key={book.id}
            book={book}
            year={year}
            month={month}
            pendingDelete={pendingDelete}
            onAskDelete={setPendingDelete}
            onUpdate={onUpdate}
            onDelete={onDelete}
          />
        ))}
      </div>

      {doneOther.length > 0 ? (
        <div className="bookgroup">
          <h3>{year}년에 다 읽은 책</h3>
          {doneOther.map((book) => (
            <BookRow
              key={book.id}
              book={book}
              year={year}
              month={month}
              pendingDelete={pendingDelete}
              onAskDelete={setPendingDelete}
              onUpdate={onUpdate}
              onDelete={onDelete}
            />
          ))}
        </div>
      ) : null}

      <form
        className="addbook"
        onSubmit={(event) => {
          event.preventDefault();
          const nextTitle = title.trim();
          if (!nextTitle) return;
          onAdd(nextTitle, author.trim());
          setTitle("");
          setAuthor("");
        }}
      >
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="책 제목"
          aria-label="책 제목"
          maxLength={120}
          required
        />
        <input
          value={author}
          onChange={(event) => setAuthor(event.target.value)}
          placeholder="지은이"
          aria-label="지은이"
          maxLength={80}
        />
        <button type="submit" className="btn">
          목록에 넣기
        </button>
      </form>
    </section>
  );
}

function BookRow({
  book,
  year,
  month,
  pendingDelete,
  onAskDelete,
  onUpdate,
  onDelete,
}: {
  book: Book;
  year: number;
  month: string;
  pendingDelete: string | null;
  onAskDelete: (id: string | null) => void;
  onUpdate: (id: string, patch: Partial<Book>) => void;
  onDelete: (id: string) => void;
}) {
  const months = Array.from({ length: 12 }, (_, index) => `${year}-${String(index + 1).padStart(2, "0")}`);
  if (book.finishedMonth && !months.includes(book.finishedMonth)) months.unshift(book.finishedMonth);

  return (
    <article className="book">
      <div>
        <h4>{book.title}</h4>
        {book.author ? <p>{book.author}</p> : null}
      </div>
      <div className="booktools">
        <div className="pills" role="group" aria-label={`${book.title} 읽기 상태`}>
          <button
            type="button"
            aria-pressed={book.status === "reading"}
            onClick={() => onUpdate(book.id, { status: "reading", finishedMonth: null })}
          >
            읽는 중
          </button>
          <button
            type="button"
            aria-pressed={book.status === "done"}
            onClick={() =>
              onUpdate(book.id, {
                status: "done",
                finishedMonth: book.finishedMonth ?? month,
              })
            }
          >
            다 읽음
          </button>
        </div>
        {book.status === "done" ? (
          <label className="monthpick">
            다 읽은 달
            <select
              value={book.finishedMonth ?? ""}
              onChange={(event) => {
                const next = event.target.value;
                if (!parseKey(next)) return;
                onUpdate(book.id, { finishedMonth: next, status: "done" });
              }}
            >
              {months.map((key) => (
                <option key={key} value={key}>
                  {monthLabel(key)}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {pendingDelete === book.id ? (
          <button
            type="button"
            className="textbtn danger"
            onClick={() => {
              onDelete(book.id);
              onAskDelete(null);
            }}
          >
            정말 지우기
          </button>
        ) : (
          <button type="button" className="textbtn" onClick={() => onAskDelete(book.id)}>
            지우기
          </button>
        )}
      </div>
    </article>
  );
}
