import { Link, useNavigate } from 'react-router-dom'
import { useTheme } from '../theme/ThemeContext'
import { useAuth } from '../auth/AuthContext'
import { useEffect, useRef, useState } from 'react'
import logoImg from '../assets/logo-img.png'

export default function Navbar() {
  const { theme, toggle } = useTheme()
  const { token, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!menuRef.current) return
      if (!menuRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  return (
    <header className="sticky top-0 z-40 backdrop-blur supports-[backdrop-filter]:bg-white/70 dark:supports-[backdrop-filter]:bg-neutral-950/40 border-b border-neutral-200/70 dark:border-neutral-800/70">
      <div className="container flex h-14 items-center justify-between">
        <Link to="/" className="font-semibold tracking-tight hover:opacity-80 transition-opacity flex items-center gap-2">
          <img src={logoImg} alt="JusticeLink Logo" className="h-8 w-8" />
          JusticeLink
        </Link>
        <div className="flex items-center gap-2" ref={menuRef}>
          {token && (
            <div className="relative">
              <button
                onClick={() => setOpen((v) => !v)}
                className="inline-flex items-center justify-center w-10 h-10 rounded-full border border-neutral-300 dark:border-neutral-700 hover:opacity-80 transition"
                aria-label="Profile"
                title="Profile"
              >
                <span>👤</span>
              </button>
              {open && (
                <div className="absolute right-0 mt-2 w-40 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-lg overflow-hidden">
                  <button onClick={() => { setOpen(false); navigate('/profile') }} className="w-full text-left px-3 py-2 text-sm hover:bg-neutral-50 dark:hover:bg-neutral-800">Profile</button>
                  <button onClick={() => { setOpen(false); navigate('/settings') }} className="w-full text-left px-3 py-2 text-sm hover:bg-neutral-50 dark:hover:bg-neutral-800">Settings</button>
                  <button onClick={() => { setOpen(false); logout(); navigate('/') }} className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-neutral-50 dark:hover:bg-neutral-800">Logout</button>
                </div>
              )}
            </div>
          )}
          <button
            onClick={toggle}
            className="group relative inline-flex items-center justify-center rounded-full border border-neutral-300 dark:border-neutral-700 w-10 h-10 transition-colors overflow-hidden"
            aria-label="Toggle theme"
            title="Toggle theme"
          >
            <span className="absolute inset-0 flex items-center justify-center transition-transform duration-300 group-hover:-translate-y-6">
              {theme === 'dark' ? '🌙' : '☀️'}
            </span>
            <span className="absolute inset-0 flex items-center justify-center transition-transform duration-300 translate-y-6 group-hover:translate-y-0">
              {theme === 'dark' ? '☀️' : '🌙'}
            </span>
          </button>
        </div>
      </div>
    </header>
  )
}
