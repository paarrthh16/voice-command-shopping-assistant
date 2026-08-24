import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Thin React wrapper around the browser's Web Speech API.
 *
 * No audio ever leaves the browser's own speech service: the hook only hands
 * the finished transcript back to the caller, which then sends the text to the
 * backend NLP endpoint.
 */

function getSpeechRecognition() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

const ERROR_MESSAGES = {
  "not-allowed": "Microphone access was blocked. Allow it in your browser settings and try again.",
  "service-not-allowed": "Microphone access was blocked by the browser.",
  "no-speech": "I couldn't hear a command. Please try again.",
  "audio-capture": "No microphone was found. Check that one is connected.",
  network: "The speech service could not be reached. Check your connection.",
  aborted: "Listening stopped.",
};

export default function useSpeechRecognition({ onResult, onError, language = "en-US" }) {
  const [supported] = useState(() => Boolean(getSpeechRecognition()));
  const [listening, setListening] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");

  const recognitionRef = useRef(null);
  const handlersRef = useRef({ onResult, onError });
  handlersRef.current = { onResult, onError };

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const start = useCallback(() => {
    const SpeechRecognitionImpl = getSpeechRecognition();
    if (!SpeechRecognitionImpl) {
      handlersRef.current.onError?.(
        "Voice input is not supported in this browser. Please use a supported browser or type your command."
      );
      return;
    }

    // Release any previous session first, so rapid clicks can never leave two
    // recognisers running with two sets of handlers attached.
    recognitionRef.current?.abort?.();

    // A fresh instance per session avoids stale state between recordings.
    const recognition = new SpeechRecognitionImpl();
    recognition.lang = language;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    let finalTranscript = "";

    recognition.onresult = (event) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) finalTranscript += result[0].transcript;
        else interim += result[0].transcript;
      }
      setInterimTranscript(interim);
    };

    recognition.onerror = (event) => {
      const message = ERROR_MESSAGES[event.error] || `Speech recognition failed (${event.error}).`;
      if (event.error !== "aborted") handlersRef.current.onError?.(message);
    };

    recognition.onend = () => {
      setListening(false);
      setInterimTranscript("");
      const transcript = finalTranscript.trim();
      if (transcript) handlersRef.current.onResult?.(transcript);
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
      setListening(true);
      setInterimTranscript("");
    } catch {
      handlersRef.current.onError?.("Could not start listening. Please try again.");
      setListening(false);
    }
  }, [language]);

  // Make sure the microphone is released if the component unmounts mid-session.
  useEffect(() => () => recognitionRef.current?.abort?.(), []);

  return { supported, listening, interimTranscript, start, stop };
}
