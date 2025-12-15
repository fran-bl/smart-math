import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "Smart Math",
    description: "Interaktivna platforma za učenje matematike",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="hr">
            <body className="antialiased">
                {children}
            </body>
        </html>
    );
}

