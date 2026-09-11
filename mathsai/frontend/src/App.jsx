import { Route, BrowserRouter, Routes, NavLink } from "react-router-dom";
import { logout } from "./api/client.js";
import Dashboard from "./pages/Dashboard.jsx";
import Lesson from "./pages/Lesson.jsx";
import Progress from "./pages/Progress.jsx";
import Questions from "./pages/Questions.jsx";

function NavBar() {
  const linkClass = ({ isActive }) =>
    `text-sm font-medium transition-colors ${
      isActive ? "text-accent" : "text-text-secondary hover:text-text-primary"
    }`;

  return (
    <header className="flex items-center justify-between border-b border-border px-6 py-4 md:px-8">
      <span className="font-display text-lg font-bold text-text-primary">MathsAI</span>
      <nav className="flex items-center gap-6">
        <NavLink to="/" end className={linkClass}>
          Dashboard
        </NavLink>
        <NavLink to="/progress" className={linkClass}>
          Progress
        </NavLink>
        <button
          type="button"
          onClick={() => logout()}
          className="text-sm font-medium text-text-secondary transition-colors hover:text-text-primary"
        >
          Sign out
        </button>
      </nav>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/lesson/:topicId" element={<Lesson />} />
        <Route path="/questions/:topicId/:difficulty" element={<Questions />} />
        <Route path="/progress" element={<Progress />} />
      </Routes>
    </BrowserRouter>
  );
}
