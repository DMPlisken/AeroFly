import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";
import { I18nProvider } from "@/i18n";
import { AerodromeDetailPage } from "@/pages/AerodromeDetail";
import { Dashboard } from "@/pages/Dashboard";
import { NotFound } from "@/pages/NotFound";
import { SearchPage } from "@/pages/Search";

export function App() {
  return (
    <I18nProvider>
      <BrowserRouter>
        <div className="shell">
          <Sidebar />
          <div className="shell-main">
            <TopBar />
            <main className="shell-body">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="/aerodromes/:icao" element={<AerodromeDetailPage />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </main>
          </div>
        </div>
      </BrowserRouter>
    </I18nProvider>
  );
}
