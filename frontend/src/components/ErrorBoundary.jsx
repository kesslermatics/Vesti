import { Component } from "react";

/**
 * Fängt JS-Fehler in Kind-Komponenten ab und zeigt statt einem Whitescreen
 * eine lesbare Fehlermeldung. Beim Tab-Wechsel wird der Fehler-State gecleart.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message || String(error) };
  }

  componentDidCatch(error, info) {
    console.error("[Vesti] Render-Fehler:", error, info?.componentStack);
  }

  // Wenn der übergebene `resetKey` sich ändert (z.B. beim Tab-Wechsel),
  // Fehler-State zurücksetzen damit der neue Tab frisch rendert.
  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, message: "" });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center py-20 px-5 text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-base font-semibold text-ink-900 mb-1">
            Hier ist etwas schiefgelaufen
          </h2>
          <p className="text-sm text-ink-700/60 max-w-xs mb-5">
            {this.state.message || "Unbekannter Fehler"}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, message: "" })}
            className="rounded-xl bg-clay-500 text-white text-sm font-medium px-5 py-2.5 hover:bg-clay-600 transition"
          >
            Nochmal versuchen
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
