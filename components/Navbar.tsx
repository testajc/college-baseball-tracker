"use client";

import Link from "next/link";
import { useSession, signOut } from "next-auth/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

export function Navbar() {
  const { data: session } = useSession();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="border-b border-border bg-background">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <Link href="/" className="text-lg font-bold text-primary">
            CBT
          </Link>
          <div className="hidden gap-4 sm:flex">
            <Link href="/players" className="text-sm hover:text-primary">Players</Link>
            <Link href="/teams" className="text-sm hover:text-primary">Teams</Link>
            <Link href="/portal" className="text-sm hover:text-primary">Portal</Link>
            {session && (
              <>
                <Link href="/favorites" className="text-sm hover:text-primary">Favorites</Link>
                <Link href="/settings" className="text-sm hover:text-primary">Settings</Link>
              </>
            )}
          </div>
        </div>

        <div className="hidden items-center gap-3 sm:flex">
          {session ? (
            <>
              <span className="text-sm text-muted-foreground">{session.user?.email}</span>
              <Button variant="outline" size="sm" onClick={() => signOut()}>Sign out</Button>
            </>
          ) : (
            <div className="flex gap-2">
              <Button variant="outline" size="sm" asChild>
                <Link href="/login">Sign in</Link>
              </Button>
              <Button size="sm" asChild>
                <Link href="/register">Register</Link>
              </Button>
            </div>
          )}
        </div>

        <button className="sm:hidden" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle menu">
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {menuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {menuOpen && (
        <div className="border-t border-border px-4 py-3 sm:hidden">
          <div className="flex flex-col gap-2">
            <Link href="/players" className="text-sm" onClick={() => setMenuOpen(false)}>Players</Link>
            <Link href="/teams" className="text-sm" onClick={() => setMenuOpen(false)}>Teams</Link>
            <Link href="/portal" className="text-sm" onClick={() => setMenuOpen(false)}>Portal</Link>
            {session && (
              <>
                <Link href="/favorites" className="text-sm" onClick={() => setMenuOpen(false)}>Favorites</Link>
                <Link href="/settings" className="text-sm" onClick={() => setMenuOpen(false)}>Settings</Link>
              </>
            )}
            {session ? (
              <button onClick={() => signOut()} className="text-left text-sm text-destructive">Sign out</button>
            ) : (
              <>
                <Link href="/login" className="text-sm text-primary" onClick={() => setMenuOpen(false)}>Sign in</Link>
                <Link href="/register" className="text-sm text-primary" onClick={() => setMenuOpen(false)}>Register</Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
