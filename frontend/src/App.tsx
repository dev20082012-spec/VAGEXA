import { Suspense, lazy, type ReactNode } from "react";
import { Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { api } from "./api/client";
import { DashboardPage, InvestigationsPage } from "./DashboardPage";
import { AccountPage, ForbiddenPage, LoginPage, NewCasePage, Shell, useSession } from "./pages";
import { Skeleton } from "./ui";
import { EvidenceTab } from "./workspace/EvidenceTab";
import { FinancialTab } from "./workspace/FinancialTab";
import { InfrastructureTab } from "./workspace/InfrastructureTab";
import { OverviewTab } from "./workspace/OverviewTab";
import { ReportTab } from "./workspace/ReportTab";
import { UnifiedTab } from "./workspace/UnifiedTab";
import { WorkspaceLayout } from "./workspace/WorkspaceLayout";

const NetworkTab = lazy(() => import("./workspace/NetworkTab"));

function Protected({ children }: { children: ReactNode }) {
  const session = useSession();
  const navigate = useNavigate();
  if (session === undefined) {
    return (
      <div style={{ padding: 32 }}>
        <Skeleton lines={3} />
      </div>
    );
  }
  if (session === null) {
    return <Navigate to="/login" replace />;
  }
  return (
    <Shell
      session={session}
      onLogout={() => {
        void api.logout().finally(() => navigate("/login"));
      }}
    >
      {children}
    </Shell>
  );
}

function Legacy({ to }: { to: string }) {
  const { caseId = "" } = useParams();
  return <Navigate to={`/cases/${caseId}/${to}`} replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <DashboardPage />
          </Protected>
        }
      />
      <Route
        path="/cases"
        element={
          <Protected>
            <InvestigationsPage />
          </Protected>
        }
      />
      <Route
        path="/cases/new"
        element={
          <Protected>
            <NewCasePage />
          </Protected>
        }
      />
      <Route
        path="/cases/:caseId"
        element={
          <Protected>
            <WorkspaceLayout />
          </Protected>
        }
      >
        <Route index element={<OverviewTab />} />
        <Route path="financial" element={<FinancialTab />} />
        <Route
          path="network"
          element={
            <Suspense fallback={<Skeleton lines={8} />}>
              <NetworkTab />
            </Suspense>
          }
        />
        <Route path="infrastructure" element={<InfrastructureTab />} />
        <Route path="unified" element={<UnifiedTab />} />
        <Route path="evidence" element={<EvidenceTab />} />
        <Route path="report" element={<ReportTab />} />
        <Route path="transactions" element={<Legacy to="financial" />} />
        <Route path="analysis" element={<Legacy to="financial?view=flow" />} />
        <Route path="graph" element={<Legacy to="network" />} />
        <Route path="correlation" element={<Legacy to="unified" />} />
      </Route>
      <Route
        path="/account"
        element={
          <Protected>
            <AccountPage />
          </Protected>
        }
      />
      <Route
        path="/forbidden"
        element={
          <Protected>
            <ForbiddenPage />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
