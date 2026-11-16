import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "THREADFLOW — Fashion Supply Chain & Merchandising Control Tower",
  description:
    "Enterprise Operations Control Tower for Inbound Procurement & Catalogue, Inventory Intelligence, and Outbound Fulfilment & Returns.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F6F5F2] text-[#18181B] selection:bg-[#1E3A8A] selection:text-white">
        {children}
      </body>
    </html>
  );
}
