/**
 * RevPilot AI — Web Frontend Application Bootstrap (React 18)
 * Conforms to:
 * - docs/28-frontend/FRONTEND-SPEC.md
 * - WCAG 2.2 AA Accessibility Navigation
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Target container 'root' not found in DOM.");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
