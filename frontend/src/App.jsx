import { useCallback, useEffect, useState } from "react";
import * as api from "./api.js";
import ErrorBanner from "./components/ErrorBanner.jsx";
import ProductCatalog from "./components/ProductCatalog.jsx";
import Recommendations from "./components/Recommendations.jsx";
import ShoppingList from "./components/ShoppingList.jsx";
import VoiceCommandPanel, { LANGUAGES } from "./components/VoiceCommandPanel.jsx";
import useSpeechRecognition from "./hooks/useSpeechRecognition.js";
import { ProductImageDefs } from "./productImages.jsx";
import { MoonIcon, SunIcon } from "./icons.jsx";
import { APP_NAME, APP_TAGLINE } from "./brand.js";

function initialTheme() {
  const stored = localStorage.getItem("apni-tokri-theme");
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function App() {
  const [items, setItems] = useState([]);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");

  const [listLoading, setListLoading] = useState(true);
  const [productsLoading, setProductsLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [busyItemIds, setBusyItemIds] = useState([]);
  const [error, setError] = useState("");

  // "assistant" is home; "browse" is the secondary full-catalog view, loaded
  // lazily so opening the app doesn't fetch 54 products it may never show.
  const [view, setView] = useState("assistant");
  const [browseLoaded, setBrowseLoaded] = useState(false);

  const [theme, setTheme] = useState(initialTheme);

  // Bumped after every change to the list so the suggestions reload with it.
  const [listVersion, setListVersion] = useState(0);
  const listChanged = () => setListVersion((version) => version + 1);

  const [language, setLanguage] = useState("en-IN");
  const [commandStatus, setCommandStatus] = useState("idle");
  const [transcript, setTranscript] = useState("");
  const [commandResult, setCommandResult] = useState(null);
  const [voiceError, setVoiceError] = useState("");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("apni-tokri-theme", theme);
  }, [theme]);

  const setItemBusy = (id, busy) =>
    setBusyItemIds((current) =>
      busy ? [...current, id] : current.filter((busyId) => busyId !== id)
    );

  const loadShoppingList = useCallback(async () => {
    setListLoading(true);
    try {
      setItems(await api.getShoppingList());
      setError("");
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
    loadShoppingList();
  }, [loadShoppingList]);

  useEffect(() => {
    if (view === "browse" && !browseLoaded) {
      setBrowseLoaded(true);
      api.getCategories().then(setCategories).catch(() => setCategories([]));
    }
  }, [view, browseLoaded]);

  useEffect(() => {
    if (!browseLoaded) return undefined;
    let cancelled = false;
    setProductsLoading(true);

    const timer = setTimeout(async () => {
      try {
        const result = await api.getProducts({ search, category });
        if (!cancelled) {
          setProducts(result);
          setError("");
        }
      } catch (loadError) {
        if (!cancelled) setError(loadError.message);
      } finally {
        if (!cancelled) setProductsLoading(false);
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search, category, browseLoaded]);

  const addItem = async (payload) => {
    setAdding(true);
    try {
      await api.addShoppingListItem(payload);
      await loadShoppingList();
      listChanged();
      setError("");
      return true;
    } catch (addError) {
      setError(addError.message);
      return false;
    } finally {
      setAdding(false);
    }
  };

  const updateItem = async (id, changes) => {
    setItemBusy(id, true);
    try {
      const updated = await api.updateShoppingListItem(id, changes);
      setItems((current) => current.map((item) => (item.id === id ? updated : item)));
      listChanged();
      setError("");
    } catch (updateError) {
      setError(updateError.message);
    } finally {
      setItemBusy(id, false);
    }
  };

  const deleteItem = async (id) => {
    setItemBusy(id, true);
    try {
      await api.deleteShoppingListItem(id);
      setItems((current) => current.filter((item) => item.id !== id));
      listChanged();
      setError("");
    } catch (deleteError) {
      setError(deleteError.message);
    } finally {
      setItemBusy(id, false);
    }
  };

  const runCommand = async (text) => {
    setTranscript(text);
    setCommandResult(null);
    setVoiceError("");
    setCommandStatus("processing");

    try {
      const response = await api.processCommand(text);
      setCommandResult(response);
      setItems(response.items);
      listChanged();
      setCommandStatus(response.success ? "success" : "error");
      setError("");
      return response.success;
    } catch (commandError) {
      setCommandStatus("error");
      setVoiceError(commandError.message);
      return false;
    }
  };

  const handleSpeechError = (message) => {
    setVoiceError(message);
    setCommandStatus("error");
  };

  const { supported, listening, interimTranscript, start, stop } = useSpeechRecognition({
    onResult: runCommand,
    onError: handleSpeechError,
    language,
  });

  const startListening = () => {
    setVoiceError("");
    setCommandResult(null);
    setTranscript("");
    setCommandStatus("listening");
    start();
  };

  useEffect(() => {
    if (!listening && commandStatus === "listening") setCommandStatus("idle");
  }, [listening, commandStatus]);

  return (
    <div className="app">
      <ProductImageDefs />

      <header className="app-header">
        <div className="brand">
          <span className="brand-word">{APP_NAME.toLowerCase()}</span>
          <span className="brand-tagline">{APP_TAGLINE}</span>
        </div>

        <div className="header-controls">
          <div className="language-picker">
            <label className="visually-hidden" htmlFor="language">Language</label>
            <select
              id="language"
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
            >
              {LANGUAGES.map(({ code, label }) => (
                <option key={code} value={code}>{label}</option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>
      </header>

      <ErrorBanner message={error} onDismiss={() => setError("")} />

      <div className="view-toggle" role="tablist" aria-label="View">
        <button type="button" role="tab" aria-selected={view === "assistant"} className={view === "assistant" ? "active" : ""} onClick={() => setView("assistant")}>
          Assistant
        </button>
        <button type="button" role="tab" aria-selected={view === "browse"} className={view === "browse" ? "active" : ""} onClick={() => setView("browse")}>
          Browse
        </button>
      </div>

      {view === "assistant" ? (
        <>
          <VoiceCommandPanel
            supported={supported}
            listening={listening}
            status={commandStatus}
            language={language}
            interimTranscript={interimTranscript}
            transcript={transcript}
            result={commandResult}
            voiceError={voiceError}
            onStart={startListening}
            onStop={stop}
            onSubmitText={runCommand}
            onAddProduct={addItem}
            adding={adding}
          />

          <div className="workspace">
            <ShoppingList
              items={items}
              loading={listLoading}
              busyItemIds={busyItemIds}
              onUpdate={updateItem}
              onDelete={deleteItem}
              onAdd={addItem}
              adding={adding}
            />

            <Recommendations listVersion={listVersion} adding={adding} onAdd={addItem} />
          </div>
        </>
      ) : (
        <ProductCatalog
          products={products}
          categories={categories}
          loading={productsLoading}
          search={search}
          category={category}
          adding={adding}
          onSearchChange={setSearch}
          onCategoryChange={setCategory}
          onAdd={addItem}
        />
      )}
    </div>
  );
}
