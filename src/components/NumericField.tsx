import { useEffect, useState } from "react";
import { formatKgInput, formatManInput, formatWonInput, parseKg, parseMan, parseWon } from "../format";

type Unit = "man" | "won" | "kg";

function parseByUnit(unit: Unit, raw: string): number | null {
  if (unit === "man") return parseMan(raw);
  if (unit === "won") return parseWon(raw);
  return parseKg(raw);
}

function formatByUnit(unit: Unit, value: number): string {
  if (unit === "man") return formatManInput(value);
  if (unit === "won") return formatWonInput(value);
  return formatKgInput(value);
}

export function NumericField({
  id,
  label,
  value,
  unit,
  aside,
  placeholder,
  onChange,
}: {
  id: string;
  label: string;
  value: number | null;
  unit: Unit;
  aside?: string | null;
  placeholder?: string;
  onChange: (value: number | null) => void;
}) {
  const [text, setText] = useState(() => (value == null ? "" : formatByUnit(unit, value)));
  const [focused, setFocused] = useState(false);
  const [invalid, setInvalid] = useState(false);

  useEffect(() => {
    if (!focused) setText(value == null ? "" : formatByUnit(unit, value));
  }, [value, unit, focused]);

  const suffix = unit === "kg" ? "kg" : unit === "won" ? "원" : "만원";

  return (
    <div className="field">
      <div className="field-top">
        <label htmlFor={id}>{label}</label>
        {aside ? <span className="aside">{aside}</span> : <span className="aside" />}
      </div>
      <div className={invalid ? "inputwrap invalid" : "inputwrap"}>
        <input
          id={id}
          inputMode={unit === "won" ? "numeric" : "decimal"}
          autoComplete="off"
          autoCorrect="off"
          placeholder={placeholder}
          aria-invalid={invalid}
          value={text}
          onFocus={() => setFocused(true)}
          onBlur={() => {
            setFocused(false);
            if (text.trim() === "") {
              setInvalid(false);
              onChange(null);
              return;
            }
            const parsed = parseByUnit(unit, text);
            if (parsed == null) {
              setInvalid(false);
              setText(value == null ? "" : formatByUnit(unit, value));
              return;
            }
            setInvalid(false);
            onChange(parsed);
            setText(formatByUnit(unit, parsed));
          }}
          onChange={(event) => {
            const raw = event.target.value;
            setText(raw);
            if (raw.trim() === "") {
              setInvalid(false);
              onChange(null);
              return;
            }
            const parsed = parseByUnit(unit, raw);
            if (parsed == null) {
              setInvalid(true);
              return;
            }
            setInvalid(false);
            onChange(parsed);
          }}
        />
        <span aria-hidden="true">{suffix}</span>
      </div>
    </div>
  );
}
