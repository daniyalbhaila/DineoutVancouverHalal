"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Discover" },
  { href: "/swipe", label: "Swipe" },
  { href: "/dineout", label: "Dine Out" },
];

export default function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--stroke)] bg-white/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 md:px-10">
        <Link href="/" className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-2xl bg-[var(--accent)] text-white shadow-sm flex items-center justify-center text-sm font-semibold">
            HF
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--ink)]">Halal Finder</p>
            <p className="text-xs text-[var(--muted)]">Vancouver</p>
          </div>
        </Link>
        <nav className="flex items-center gap-2">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-full px-3 py-1 text-sm transition ${
                  active
                    ? "bg-[var(--accent)] text-white"
                    : "text-[var(--muted)] hover:text-[var(--ink)]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
