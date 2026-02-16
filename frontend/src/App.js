import { useState } from "react";
import "@/App.css";
import { HashRouter, Routes, Route } from "react-router-dom";
import LandingPage from "@/pages/LandingPage";
import OnboardingPage from "@/pages/OnboardingPage";
import DashboardPage from "@/pages/DashboardPage";
import SharePage from "@/pages/SharePage";
import { Toaster } from "@/components/ui/sonner";

function App() {
  const [userData, setUserData] = useState(() => {
    const stored = localStorage.getItem("pam_user");
    return stored ? JSON.parse(stored) : null;
  });

  const saveUser = (user) => {
    setUserData(user);
    localStorage.setItem("pam_user", JSON.stringify(user));
  };

  const clearUser = () => {
    setUserData(null);
    localStorage.removeItem("pam_user");
    localStorage.removeItem("pam_session_id");
  };

  return (
    <div className="noise-overlay min-h-screen">
      <Toaster position="top-right" richColors />
      <HashRouter>
        <Routes>
          <Route path="/" element={<LandingPage user={userData} />} />
          <Route
            path="/onboarding"
            element={<OnboardingPage onSaveUser={saveUser} />}
          />
          <Route
            path="/dashboard"
            element={
              <DashboardPage
                user={userData}
                onSaveUser={saveUser}
                onLogout={clearUser}
              />
            }
          />
          <Route path="/share/:shareId" element={<SharePage />} />
        </Routes>
      </HashRouter>
    </div>
  );
}

export default App;
