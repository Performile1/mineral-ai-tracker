import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { getCurrentUser } from "@/lib/auth";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Mineral AI Tracker - Buffett-Radar",
  description: "Deterministic, self-learning investment tool for mineral assets",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const user = await getCurrentUser();
  return (
    <html lang="en">
      <body className={inter.className}>
        {/* Navigation */}
        <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              <Link href="/" className="text-xl font-bold text-primary">
                Mineral AI Tracker
              </Link>
              <div className="flex gap-6">
                <Link href="/" className="text-primary hover:opacity-70 transition-opacity">
                  Dashboard
                </Link>
                <Link href="/assets" className="text-primary hover:opacity-70 transition-opacity">
                  Assets
                </Link>
                <Link href="/pulse" className="text-primary hover:opacity-70 transition-opacity font-semibold">
                  Global Pulse
                </Link>
                <Link href="/analytics" className="text-primary hover:opacity-70 transition-opacity">
                  Analytics
                </Link>
                <Link href="/settings" className="text-primary hover:opacity-70 transition-opacity">
                  Settings
                </Link>
                {user ? (
                  <div className="flex items-center gap-3 ml-6 border-l border-gray-200 pl-6">
                    <span className="text-sm text-gray-600">{user.name || user.email}</span>
                    <a
                      href="/api/auth/signout"
                      className="text-sm text-primary hover:opacity-70 transition-opacity"
                    >
                      Sign Out
                    </a>
                  </div>
                ) : (
                  <Link
                    href="/api/auth/signin"
                    className="ml-6 px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90 transition-opacity"
                  >
                    Sign In
                  </Link>
                )}
              </div>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
