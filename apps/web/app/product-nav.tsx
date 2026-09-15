import Link from "next/link";

export function ProductNav() {
  return (
    <nav className="journey-nav" aria-label="Jornada operacional">
      <Link href="/">Central</Link>
      <Link href="/check-in">Check-in</Link>
      <Link href="/financeiro">Financeiro</Link>
    </nav>
  );
}
