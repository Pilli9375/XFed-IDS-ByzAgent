import { Navigate, Route, Routes } from 'react-router-dom';
import { useBackendStatus } from './api/useBackendStatus';
import Footer from './layout/Footer';
import Sidebar from './layout/Sidebar';
import ClientTrustMonitor from './sections/ClientTrustMonitor';
import Detect from './sections/Detect';
import Explain from './sections/Explain';
import ExplanationAgreement from './sections/ExplanationAgreement';
import Faithfulness from './sections/Faithfulness';
import FederationStatus from './sections/FederationStatus';
import MethodsLimits from './sections/MethodsLimits';
import PlaceholderSection from './sections/PlaceholderSection';
import { SECTIONS } from './sections/registry';

// Sections get their real component here as they're built; anything not
// listed still falls back to PlaceholderSection.
const SECTION_COMPONENTS = {
  'federation-status': FederationStatus,
  detect: Detect,
  explain: Explain,
  'explanation-agreement': ExplanationAgreement,
  'client-trust-monitor': ClientTrustMonitor,
  faithfulness: Faithfulness,
  'methods-limits': MethodsLimits,
};

export default function App() {
  const status = useBackendStatus();

  return (
    <div className="xf-app">
      <Sidebar status={status} />
      <main className="xf-main">
        <Routes>
          <Route path="/" element={<Navigate to={SECTIONS[0].path} replace />} />
          {SECTIONS.map(({ key, path, ...section }) => {
            const Component = SECTION_COMPONENTS[key] ?? PlaceholderSection;
            return <Route key={key} path={path} element={<Component {...section} />} />;
          })}
        </Routes>
        <Footer />
      </main>
    </div>
  );
}
