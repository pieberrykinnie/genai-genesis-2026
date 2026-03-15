import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DataSite Impact Analyzer",
  description: "AI-assisted data centre impact assessment for Canadian municipalities",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
