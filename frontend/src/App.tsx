import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'

import Login from './pages/Login'
import Register from './pages/Register'
import OAuthCallback from './pages/OAuthCallback'
import PrivateRoute from './components/PrivateRoute'
import PWAInstallPrompt from './components/PWAInstallPrompt'
import LoadingSpinner from './components/LoadingSpinner'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { WebSocketProvider } from './components/WebSocketProvider'

// Lazy load des pages pour améliorer les performances
const Dashboard = lazy(() => import('./pages/Dashboard'))
const SharePage = lazy(() => import('./pages/SharePage'))
const TrashPage = lazy(() => import('./pages/TrashPage'))
const HomePage = lazy(() => import('./pages/HomePage'))
const AboutPage = lazy(() => import('./pages/AboutPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const MyFilesPage = lazy(() => import('./pages/MyFilesPage'))
const SharedFilesPage = lazy(() => import('./pages/SharedFilesPage'))

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <WebSocketProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/share/:token" element={<SharePage />} />
            <Route path="/auth/callback" element={<OAuthCallback />} />
            <Route
              path="/dashboard"
              element={
                <PrivateRoute>
                  <Suspense fallback={<LoadingSpinner />}>
                    <Dashboard />
                  </Suspense>
                </PrivateRoute>
              }
            />
            <Route
              path="/trash"
              element={
                <PrivateRoute>
                  <Suspense fallback={<LoadingSpinner />}>
                    <TrashPage />
                  </Suspense>
                </PrivateRoute>
              }
            />
            <Route
              path="/home"
              element={
                <PrivateRoute>
                  <Suspense fallback={<LoadingSpinner />}>
                    <HomePage />
                  </Suspense>
                </PrivateRoute>
              }
            />
            <Route
              path="/about"
              element={
                <PrivateRoute>
                  <Suspense fallback={<LoadingSpinner />}>
                    <AboutPage />
                  </Suspense>
                </PrivateRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <PrivateRoute>
                  <Suspense fallback={<LoadingSpinner />}>
                    <ChatPage />
                  </Suspense>
                </PrivateRoute>
              }
            />
            <Route
              path="/my-files"
              element={
                <PrivateRoute>
                  <Suspense fallback={<LoadingSpinner />}>
                    <MyFilesPage />
                  </Suspense>
                </PrivateRoute>
              }
            />
            <Route
              path="/shared"
              element={
                <PrivateRoute>
                  <Suspense fallback={<LoadingSpinner />}>
                    <SharedFilesPage />
                  </Suspense>
                </PrivateRoute>
              }
            />
            <Route
              path="/share/:token"
              element={
                <Suspense fallback={<LoadingSpinner />}>
                  <SharePage />
                </Suspense>
              }
            />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          <PWAInstallPrompt />
        </Router>
        <ToastContainer position="top-right" autoClose={3000} />
          </WebSocketProvider>
      </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App

