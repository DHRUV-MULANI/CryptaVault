import './index.css';
import { Route, Router, Switch, useLocation } from 'wouter';
import { useHashLocation } from 'wouter/use-hash-location';
import { ShieldCheck } from 'lucide-react';
import { ToastProvider } from './components/ui';
import Layout from './components/Layout';
import { VaultProvider, useVault } from './lib/vault';
import AuthPage from './pages/AuthPage';
import Dashboard from './pages/Dashboard';
import VaultPage from './pages/VaultPage';
import SharesPage from './pages/SharesPage';
import MessagesPage from './pages/MessagesPage';
import CatalogPage from './pages/CatalogPage';
import AcademyPage from './pages/AcademyPage';
import AdminPage from './pages/AdminPage';
import SettingsPage from './pages/SettingsPage';
import StatusPage from './pages/StatusPage';
import ShareViewer from './pages/ShareViewer';

function LoadingScreen(): JSX.Element {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-glow">
          <ShieldCheck className="h-6 w-6" />
        </span>
        <div className="text-sm text-slate-400">Opening local vault…</div>
        <div className="h-1 w-40 overflow-hidden rounded-full bg-white/10">
          <div className="shimmer h-full w-full" />
        </div>
      </div>
    </div>
  );
}

function NotFound(): JSX.Element {
  return (
    <div className="card mx-auto max-w-lg p-8 text-center">
      <div className="text-5xl font-semibold text-white">404</div>
      <p className="mt-2 text-sm text-slate-400">
        This route does not exist in the CryptaVault portal.
      </p>
      <a href="#/" className="btn-primary mt-5 inline-flex">
        Back to overview
      </a>
    </div>
  );
}

function Shell(): JSX.Element {
  const { status } = useVault();
  const [location] = useLocation();

  if (location.startsWith('/share')) {
    return <ShareViewer />;
  }

  if (status === 'loading') return <LoadingScreen />;
  if (status !== 'unlocked') return <AuthPage />;

  return (
    <Layout>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/vault" component={VaultPage} />
        <Route path="/shares" component={SharesPage} />
        <Route path="/messages" component={MessagesPage} />
        <Route path="/catalog" component={CatalogPage} />
        <Route path="/academy" component={AcademyPage} />
        <Route path="/admin" component={AdminPage} />
        <Route path="/settings" component={SettingsPage} />
        <Route path="/status" component={StatusPage} />
        <Route component={NotFound} />
      </Switch>
    </Layout>
  );
}

export default function App(): JSX.Element {
  return (
    <Router hook={useHashLocation}>
      <ToastProvider>
        <VaultProvider>
          <Shell />
        </VaultProvider>
      </ToastProvider>
    </Router>
  );
}
