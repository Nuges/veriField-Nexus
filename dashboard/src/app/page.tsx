import { Navbar } from "@/components/landing/Navbar";
import { HeroSection } from "@/components/landing/HeroSection";
import { ProblemSection } from "@/components/landing/ProblemSection";
import { PlatformWorkflowSection } from "@/components/landing/PlatformWorkflowSection";
import { ClimateSectorsSection } from "@/components/landing/ClimateSectorsSection";
import { IntegrationsSection } from "@/components/landing/IntegrationsSection";
import { PilotMapSection } from "@/components/landing/PilotMapSection";
import { CtaSection } from "@/components/landing/CtaSection";
import { Footer } from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white font-sans antialiased selection:bg-[#00B47A]/30 selection:text-zinc-900">
      <Navbar />
      <main>
        <HeroSection />
        <ProblemSection />
        <PlatformWorkflowSection />
        <ClimateSectorsSection />
        <IntegrationsSection />
        <PilotMapSection />
        <CtaSection />
      </main>
      <Footer />
    </div>
  );
}
