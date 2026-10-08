import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import ClassificationPage from "./pages/document/ClassificationPage.jsx";
import DocumentLayout from "./pages/document/DocumentLayout.jsx";
import EntitiesPage from "./pages/document/EntitiesPage.jsx";
import ExportPage from "./pages/document/ExportPage.jsx";
import KeywordsPage from "./pages/document/KeywordsPage.jsx";
import OverviewPage from "./pages/document/OverviewPage.jsx";
import PreprocessingPage from "./pages/document/PreprocessingPage.jsx";
import SimilarityPage from "./pages/document/SimilarityPage.jsx";
import StatisticsPage from "./pages/document/StatisticsPage.jsx";
import SummaryPage from "./pages/document/SummaryPage.jsx";
import DocumentsPage from "./pages/DocumentsPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import UploadPage from "./pages/UploadPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="documents/:id" element={<DocumentLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="preprocessing" element={<PreprocessingPage />} />
          <Route path="keywords" element={<KeywordsPage />} />
          <Route path="entities" element={<EntitiesPage />} />
          <Route path="classification" element={<ClassificationPage />} />
          <Route path="summary" element={<SummaryPage />} />
          <Route path="similarity" element={<SimilarityPage />} />
          <Route path="statistics" element={<StatisticsPage />} />
          <Route path="export" element={<ExportPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
