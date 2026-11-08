import { useState, type ChangeEvent, type FormEvent } from "react";
import { ApiError, FALLBACK_ERROR_MESSAGE, getHello } from "../api/client";

const NAME_MAX_LENGTH = 40;

type Result = { kind: "success"; text: string } | { kind: "error"; text: string } | null;

export default function Welcome() {
  const [name, setName] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<Result>(null);

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    setName(event.target.value.slice(0, NAME_MAX_LENGTH));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setResult(null);
    try {
      const { message } = await getHello(name.slice(0, NAME_MAX_LENGTH));
      setResult({ kind: "success", text: message });
    } catch (error) {
      const text = error instanceof ApiError ? error.message : FALLBACK_ERROR_MESSAGE;
      setResult({ kind: "error", text });
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="welcome">
      <h1>Welcome to Canasta</h1>
      <p>Canasta is a classic rummy-style card game for two to six players.</p>
      <form onSubmit={(event) => void handleSubmit(event)}>
        <label htmlFor="player-name">Your name</label>
        <input
          id="player-name"
          type="text"
          value={name}
          maxLength={NAME_MAX_LENGTH}
          onChange={handleChange}
          autoComplete="off"
        />
        <button type="submit" disabled={pending}>
          {pending ? "Pinging…" : "Ping API"}
        </button>
      </form>
      {result?.kind === "success" && <p role="status">{result.text}</p>}
      {result?.kind === "error" && <p role="alert">{result.text}</p>}
    </section>
  );
}
