"use client";

import {
  LandingNav,
  HeroSection,
  StatsBar,
  FeaturesSection,
  HowItWorksSection,
  ClinicalServicesSection,
  VisionarySection,
  FooterCTA,
} from "@/components/landing-sections";

export function LandingPageContent() {
  return (
    <div className="min-h-screen bg-white">
      <LandingNav />
      <HeroSection />
      <StatsBar />
      <FeaturesSection />
      <HowItWorksSection />
      <ClinicalServicesSection />
      <VisionarySection />
      <FooterCTA />
      <footer className="border-t border-white/10 bg-[#0f172a] py-6 text-center">
        <p className="text-sm text-blue-300/50">
          &copy; 2026 NeuroHub. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
