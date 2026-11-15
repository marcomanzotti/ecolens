import type { Metadata, Viewport } from "next";
import "@fontsource/overpass/400.css";
import "@fontsource/overpass/400-italic.css";
import "@fontsource/overpass/700.css";
import "@fontsource/fira-sans/500.css";
import "@fontsource/fira-sans/700.css";
import "@fontsource/fira-sans/900.css";
import "./globals.css";
import { ReferenceDataProvider } from "@/components/providers/reference-data";
import { SiteFooter } from "@/components/site/site-footer";

export const metadata: Metadata = {
  title: {
    default: "EcoLens",
    template: "%s · EcoLens",
  },
  description:
    "Pick a place on Earth and find out what is changing there, by how much, and whether the change is statistically significant.",
};

export const viewport: Viewport = {
  themeColor: "#07173f",
  colorScheme: "dark",
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased" data-scroll-behavior="smooth">
      <body className="flex min-h-full flex-col">
        <a
          href="#main"
          className="sr-only z-50 rounded-md bg-white px-4 py-2 font-bold text-deep focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
        >
          Skip to content
        </a>
        <ReferenceDataProvider>
          {children}
          <SiteFooter />
        </ReferenceDataProvider>
      </body>
    </html>
  );
}
