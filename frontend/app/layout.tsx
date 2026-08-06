import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Codebook Monitoring",
  description: "Lightweight health checks for servers, databases, and services",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
