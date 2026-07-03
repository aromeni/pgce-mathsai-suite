import { Route, BrowserRouter, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Lesson from "./pages/Lesson.jsx";
import Progress from "./pages/Progress.jsx";
import Questions from "./pages/Questions.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/lesson/:topicId" element={<Lesson />} />
        <Route path="/questions/:topicId/:difficulty" element={<Questions />} />
        <Route path="/progress" element={<Progress />} />
      </Routes>
    </BrowserRouter>
  );
}
