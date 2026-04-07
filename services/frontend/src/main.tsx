import React from "react";
import ReactDOM from "react-dom/client";

function App() {
  return (
    <div>
      <h1>AeroFly</h1>
      <p>Aerodrome Compendium — Deutsche Flugplatzdaten</p>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
