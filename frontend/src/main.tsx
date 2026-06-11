import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import SharePage from "./components/SharePage";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/c/:sessionId" element={<App />} />
        <Route path="/share/:token" element={<SharePage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
