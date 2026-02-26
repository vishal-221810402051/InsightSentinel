import { BrowserRouter, Route, Routes } from "react-router-dom";

import AppShell from "./layout/AppShell";
import DatasetDetail from "./pages/DatasetDetail";
import Overview from "./pages/Overview";

export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/datasets/:id" element={<DatasetDetail />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
