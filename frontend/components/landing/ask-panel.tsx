"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { Sparkles } from "lucide-react";
import { toApiError, type AsyncState } from "@/hooks/use-api";
import { api, type AskResult, type Catalog } from "@/lib/api";
import { placeName } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { ErrorNotice } from "@/components/ui/async-view";

const MIN_LENGTH = 3;
const MAX_LENGTH = 500;
const EXAMPLES = [
  "Is the Sahel getting wetter?",
  "Is it getting hotter in Delhi?",
  "Is the snow disappearing in the Alps?",
] as const;

interface AskPanelProps {
  catalog: Catalog;
  /** Fill the guided questions with what was understood. */
  onUse: (result: AskResult) => void;
}

/** Free text in, a place and catalog variables out. Never numbers or verdicts. */
export function AskPanel({ catalog, onUse }: AskPanelProps) {
  const [question, setQuestion] = useState("");
  const [state, setState] = useState<AsyncState<AskResult>>({ status: "idle" });
  const [showTooShort, setShowTooShort] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const fieldId = useId();
  const hintId = useId();
  const trimmed = question.trim();
  const tooShort = trimmed.length < MIN_LENGTH;

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setShowTooShort(tooShort);
    if (tooShort) return;
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setState({ status: "loading" });
    try {
      const data = await api.ask({ question: trimmed }, current.signal);
      if (!current.signal.aborted) setState({ status: "success", data });
    } catch (cause) {
      if (!current.signal.aborted) setState({ status: "error", error: toApiError(cause) });
    }
  };

  const variableNames = (result: AskResult) =>
    result.variable_ids
      .map((id) => catalog.variables.find((variable) => variable.id === id)?.name)
      .filter((name): name is string => Boolean(name));

  return (
    <div className="space-y-4">
      <form onSubmit={submit} className="space-y-3">
        <label htmlFor={fieldId} className="block font-heading text-base font-bold">
          Your question
        </label>
        <textarea
          id={fieldId}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={MAX_LENGTH}
          rows={3}
          enterKeyHint="send"
          placeholder={EXAMPLES[0]}
          aria-describedby={showTooShort && tooShort ? `${hintId}-error ${hintId}` : hintId}
          aria-invalid={(showTooShort && tooShort) || undefined}
          className="w-full resize-none rounded-lg border border-line-strong bg-deep p-3 text-white placeholder:text-muted-foreground hover:border-white"
        />
        {showTooShort && tooShort ? (
          <p id={`${hintId}-error`} role="alert" className="font-bold text-neon">
            Write a question of at least {MIN_LENGTH} characters.
          </p>
        ) : null}
        <p id={hintId} className="text-sm text-muted-foreground">
          The assistant only works out the place and the variables. It never computes a number or a
          verdict: the statistics do.
        </p>
        <Button type="submit" disabled={state.status === "loading"}>
          <Sparkles aria-hidden="true" />
          {state.status === "loading" ? "Reading your question…" : "Read my question"}
        </Button>
        <p className="flex flex-wrap items-center gap-x-1 text-sm text-muted-foreground">
          <span>Or try:</span>
          {EXAMPLES.slice(1).map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setQuestion(example)}
              className="min-h-11 cursor-pointer rounded-md px-1.5 underline underline-offset-4 hover:text-white"
            >
              {example}
            </button>
          ))}
        </p>
      </form>

      <div aria-live="polite">
        {state.status === "error" ? <ErrorNotice error={state.error} /> : null}
        {state.status === "success" ? (
          <div className="space-y-3 rounded-lg border border-line-strong p-4">
            <p className="font-bold">{state.data.interpretation}</p>
            {state.data.understood ? (
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
                <dt className="text-muted-foreground">Place</dt>
                <dd>
                  {state.data.location
                    ? placeName(state.data.location)
                    : "Not found: pick one below"}
                </dd>
                <dt className="text-muted-foreground">Variables</dt>
                <dd>{variableNames(state.data).join(", ") || "The whole line-up"}</dd>
              </dl>
            ) : null}
            <Button variant="accent" onClick={() => onUse(state.data)}>
              {state.data.understood ? "Use this in the questions" : "Answer the questions instead"}
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
