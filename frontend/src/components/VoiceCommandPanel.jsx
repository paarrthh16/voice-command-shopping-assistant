import { useState } from "react";
import { formatAmount } from "../format.js";
import { CURRENCY } from "../api.js";
import { AlertIcon, CheckIcon, ChevronRightIcon, MicIcon, StopIcon } from "../icons.jsx";
import SearchResults from "./SearchResults.jsx";
import { RecommendationList } from "./Recommendations.jsx";

export const LANGUAGES = [
  { code: "en-IN", label: "English", short: "en" },
  { code: "hi-IN", label: "हिंदी (Hindi)", short: "hi" },
];

const INTENT_LABELS = {
  ADD_ITEM: "Add",
  REMOVE_ITEM: "Remove",
  UPDATE_ITEM: "Update",
  SHOW_LIST: "Show list",
  CLEAR_LIST: "Clear list",
  SEARCH_PRODUCT: "Search",
  RECOMMEND: "Show recommendations",
  UNKNOWN: "Not understood",
};

const STATUS_TEXT = {
  idle: "Tap the mic, or type a command",
  listening: "Listening…",
  processing: "Understanding…",
  success: "Command completed",
  error: "Could not complete that command",
};

// Example commands, shown as chips. Clicking one runs it through the very same
// pipeline as speech — no second command system.
const EXAMPLES = {
  "en-IN": [
    { label: "Add milk", command: "add milk" },
    { label: "Find toothpaste", command: "find toothpaste" },
    { label: "What should I buy?", command: "show recommendations" },
  ],
  "hi-IN": [
    { label: "दूध जोड़ो", command: "दूध जोड़ो" },
    { label: "टूथपेस्ट खोजो", command: "टूथपेस्ट खोजो" },
    { label: "मुझे क्या खरीदना चाहिए", command: "मुझे क्या खरीदना चाहिए" },
  ],
};

/**
 * The unified command bar: one control that supports typing and speaking,
 * with a single mic/submit affordance rather than two separate paths.
 * Below it: transcript, interpretation, result, and any search/recommendation
 * output the command produced.
 */
export default function VoiceCommandPanel({
  supported,
  listening,
  status,
  language,
  interimTranscript,
  transcript,
  result,
  voiceError,
  onStart,
  onStop,
  onSubmitText,
  onAddProduct,
  adding,
}) {
  const [typedCommand, setTypedCommand] = useState("");
  const processing = status === "processing";
  const isHindi = language.startsWith("hi");
  const examples = EXAMPLES[language] || EXAMPLES["en-IN"];
  const hasError = status === "error";

  const handleSubmit = async (event) => {
    event.preventDefault();
    const text = typedCommand.trim();
    if (!text) return;
    const handled = await onSubmitText(text);
    if (handled) setTypedCommand("");
  };

  // The bar's one button does the obvious thing: submit typed text if there
  // is any, otherwise toggle the microphone.
  const handleBarButton = () => {
    if (typedCommand.trim()) {
      handleSubmit({ preventDefault() {} });
      return;
    }
    if (listening) onStop();
    else onStart();
  };

  const interpretation = [];
  if (result) {
    interpretation.push(["Action", INTENT_LABELS[result.intent] || result.intent]);
    if (result.item) interpretation.push(["Item", result.item]);
    if (result.quantity) {
      interpretation.push(["Quantity", formatAmount(result.quantity, result.unit)]);
    }
    const filters = result.filters;
    if (filters?.query) interpretation.push(["Product", filters.query]);
    if (filters?.brand) interpretation.push(["Brand", filters.brand]);
    if (filters?.size) interpretation.push(["Size", filters.size]);
    if (filters?.min_price != null && filters?.max_price != null) {
      interpretation.push([
        "Price",
        `${CURRENCY}${filters.min_price} – ${CURRENCY}${filters.max_price}`,
      ]);
    } else if (filters?.max_price != null) {
      interpretation.push(["Maximum price", `${CURRENCY}${filters.max_price}`]);
    } else if (filters?.min_price != null) {
      interpretation.push(["Minimum price", `${CURRENCY}${filters.min_price}`]);
    }
  }

  return (
    <section className="card voice-panel" aria-label="Voice command">
      <span className="block-label">Say or type what you need</span>

      <div className="command-bar-wrap">
        <form className="command-bar" onSubmit={handleSubmit}>
          <label className="visually-hidden" htmlFor="command-input">
            Say or type a command
          </label>
          <input
            id="command-input"
            type="text"
            value={typedCommand}
            disabled={listening || processing}
            placeholder={
              listening
                ? "Listening…"
                : isHindi
                ? "जैसे: दो बोतल पानी जोड़ो"
                : "e.g. Add 2 bottles of water"
            }
            aria-label="Command"
            onChange={(event) => setTypedCommand(event.target.value)}
          />
          {supported && (
            <button
              type="button"
              className={`mic-dot ${listening ? "listening" : ""} ${processing ? "processing" : ""} ${hasError ? "error-state" : ""}`}
              onClick={handleBarButton}
              disabled={processing}
              aria-pressed={listening}
              aria-label={
                typedCommand.trim() ? "Send command" : listening ? "Stop listening" : "Start voice command"
              }
            >
              {listening ? <StopIcon /> : <MicIcon />}
            </button>
          )}
          {!supported && (
            <button type="submit" className="command-submit" disabled={processing || !typedCommand.trim()} aria-label="Send command">
              <ChevronRightIcon />
            </button>
          )}
        </form>

        <p className={`voice-status-line ${status}`} role="status" aria-live="polite">
          {processing && <span className="spinner" aria-hidden="true" />}
          {STATUS_TEXT[status] || STATUS_TEXT.idle}
        </p>

        {!supported && (
          <p className="mic-unsupported-note">
            Voice input isn't supported in this browser — Chrome or Edge add it. Typing works everywhere.
          </p>
        )}

        {listening && interimTranscript && <p className="interim">"{interimTranscript}"</p>}

        <ul className="example-chips">
          {examples.map(({ label, command }) => (
            <li key={command}>
              <button
                type="button"
                className="chip-button"
                disabled={processing}
                onClick={() => onSubmitText(command)}
              >
                {label}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {transcript && (
        <div className="transcript-block">
          <span className="block-label">{isHindi ? "आपने कहा · You said" : "You said"}</span>
          <p className="said-line" lang={isHindi ? "hi" : "en"}>
            "{transcript}"
          </p>
          {result?.understood_as && (
            <p className="translated">Read as: "{result.understood_as}"</p>
          )}
        </div>
      )}

      {result && (
        <div className="understood-block">
          <span className="block-label">I understood</span>
          <dl className="interpretation">
            {interpretation.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>

          <p className={result.success ? "outcome ok" : "outcome fail"}>
            {result.success ? <CheckIcon /> : <AlertIcon />}
            {result.message}
          </p>

          {result.intent === "SEARCH_PRODUCT" && (
            <SearchResults
              results={result.results || []}
              substitutes={result.substitutes || []}
              adding={adding}
              onAdd={onAddProduct}
            />
          )}

          {result.intent === "RECOMMEND" && (result.recommendations || []).length > 0 && (
            <RecommendationList
              recommendations={result.recommendations}
              adding={adding}
              onAdd={onAddProduct}
            />
          )}
        </div>
      )}

      {voiceError && (
        <p className="outcome fail" role="alert">
          <AlertIcon />
          {voiceError}
        </p>
      )}
    </section>
  );
}
