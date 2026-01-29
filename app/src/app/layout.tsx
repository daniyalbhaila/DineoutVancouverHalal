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
  title: "Dine Out Vancouver Halal Finder",
  description:
    "Filter Dine Out Vancouver menus for halal-friendly options and clear price ranges.",
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
