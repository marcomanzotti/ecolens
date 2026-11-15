import type { Metadata } from "next";
import { TourView } from "@/components/tour/tour-view";

export const metadata: Metadata = {
  title: "Watch a solved case",
};

export default function TourPage() {
  return (
    <main id="main" className="flex-1">
      <h1 className="sr-only">Watch a solved case</h1>
      <TourView />
    </main>
  );
}
