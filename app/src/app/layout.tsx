import type { Metadata } from "next";
import { Manrope, Newsreader } from "next/font/google";
import "./globals.css";
import SiteHeader from "../components/SiteHeader";

const manrope = Manrope({
  variable: "--font-sans",
  subsets: ["latin"],
});

const newsreader = Newsreader({
  variable: "--font-display",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://vancouverhalal.vercel.app"),
  title: {
    default: "Vancouver Halal Finder + Dine Out",
    template: "%s · Vancouver Halal Finder",
  },
  description:
    "Discover halal-friendly restaurants in Vancouver and filter Dine Out Vancouver menus with clear confidence and pricing.",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "Vancouver Halal Finder + Dine Out",
    description:
      "Discover halal-friendly restaurants in Vancouver and filter Dine Out Vancouver menus with clear confidence and pricing.",
    url: "/",
    siteName: "Vancouver Halal Finder",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Vancouver Halal Finder + Dine Out",
    description:
      "Discover halal-friendly restaurants in Vancouver and filter Dine Out Vancouver menus with clear confidence and pricing.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${newsreader.variable} antialiased`}>
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
