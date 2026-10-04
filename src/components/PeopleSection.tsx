import type { People } from "../model";

const FIELDS: { key: keyof People; label: string; placeholder: string; rows: number }[] = [
  { key: "grateful", label: "고마웠던 사람", placeholder: "이름, 그리고 무슨 일이었는지", rows: 2 },
  { key: "distant", label: "오래 못 본 사람", placeholder: "이름", rows: 2 },
  { key: "reach", label: "다음 달에 먼저 연락할 사람", placeholder: "이름. 다음 달에 여기 다시 보입니다", rows: 2 },
  { key: "note", label: "더 적어 두고 싶은 말", placeholder: "없어도 됩니다", rows: 3 },
];

export function PeopleSection({
  month,
  people,
  previousReach,
  onChange,
}: {
  month: string;
  people: People;
  previousReach: string;
  onChange: (people: People) => void;
}) {
  return (
    <section id="people" aria-labelledby="people-title">
      <header className="sec-h">
        <h2 id="people-title">
          <span>04</span>사람
        </h2>
        <p>한 달에 한 번, 이름만 적어도 됩니다.</p>
      </header>
      {previousReach.trim() ? (
        <p className="recall">
          <span>지난달에 연락하기로 한 사람</span>
          {previousReach}
        </p>
      ) : null}
      {FIELDS.map((field) => (
        <label key={field.key} className="note" htmlFor={`${month}-${field.key}`}>
          {field.label}
          <textarea
            id={`${month}-${field.key}`}
            rows={field.rows}
            maxLength={field.key === "note" ? 800 : 400}
            placeholder={field.placeholder}
            value={people[field.key]}
            onChange={(event) => onChange({ ...people, [field.key]: event.target.value })}
          />
        </label>
      ))}
    </section>
  );
}
