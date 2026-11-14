import { useAuth } from '@clerk/clerk-react';
import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

const Test = lazy(() => import('./pages/Test'));
const Login = lazy(() => import('./pages/Login'));
const FileUploader = lazy(() => import('./pages/FileUploader'));

function Loading() {
  return <p className="shell loading" role="status">Loading…</p>;
}

function UploadRoute() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <Loading />;
  return isSignedIn ? <FileUploader /> : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/upload" element={<UploadRoute />} />
        <Route path="/test" element={<Test />} />
      </Routes>
    </Suspense>
  );
}
