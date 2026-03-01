"use client";

import { useState, useRef } from "react";
import Link from "next/link";
/* eslint-disable @next/next/no-img-element */
import { useT, useLocale } from "@/lib/i18n";
import { motion, useInView } from "motion/react";
import { Brain, List, X, Globe } from "phosphor-react";
import { AuroraBackground } from "@/components/ui/aurora-background";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { MovingBorder } from "@/components/ui/moving-border";
import { BentoGrid, BentoGridItem } from "@/components/ui/bento-grid";
import { CardContainer, CardBody, CardItem } from "@/components/ui/3d-card";
import { SpotlightCard } from "@/components/ui/spotlight";
import { WavyBackground } from "@/components/ui/wavy-background";
import { BrainNetwork } from "@/components/svg/brain-network";
import { PipelineFlow } from "@/components/svg/pipeline-flow";
import { ModalityWave } from "@/components/svg/modality-wave";
import { QualityScan } from "@/components/svg/quality-scan";
import { FusionConvergence } from "@/components/svg/fusion-convergence";
import { ReportGenerate } from "@/components/svg/report-generate";
import { ShieldSecure } from "@/components/svg/shield-secure";
import { UploadIcon, AnalysisIcon, ResultsIcon, ReportDownloadIcon } from "@/components/svg/step-icons";
import { EpilepsyIcon, DementiaIcon, ParkinsonIcon, TumorIcon } from "@/components/svg/clinical-icons";

/* ── Shared: Gradient mesh background for futuristic sections ── */
function GradientMesh({ variant = "blue" }: { variant?: "blue" | "indigo" | "dark" }) {
  const colors = {
    blue: { from: "#0b6bcb", via: "#3b82f6", to: "#dbeafe" },
    indigo: { from: "#4f46e5", via: "#6366f1", to: "#e0e7ff" },
    dark: { from: "#0f172a", via: "#1e3a5f", to: "#0b6bcb" },
  };
  const c = colors[variant];
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div
        className="absolute -inset-[50%] opacity-[0.07]"
        style={{
          backgroundImage: `radial-gradient(ellipse at 20% 50%, ${c.from} 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, ${c.via} 0%, transparent 50%), radial-gradient(ellipse at 50% 80%, ${c.to} 0%, transparent 50%)`,
          animation: "aurora 40s linear infinite",
        }}
      />
      {/* Grid pattern overlay */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(${c.from} 1px, transparent 1px), linear-gradient(90deg, ${c.from} 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />
    </div>
  );
}

/* ── Floating particles for futuristic feel ── */
function FloatingParticles({ count = 12 }: { count?: number }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={`particle-${i}`}
          className="absolute h-1 w-1 rounded-full bg-[#0b6bcb]"
          style={{
            left: `${10 + (i * 73) % 80}%`,
            top: `${15 + (i * 47) % 70}%`,
          }}
          animate={{
            y: [0, -20, 0],
            opacity: [0.1, 0.4, 0.1],
          }}
          transition={{
            duration: 3 + (i % 3),
            delay: i * 0.4,
            repeat: Number.POSITIVE_INFINITY,
          }}
        />
      ))}
    </div>
  );
}

/* ── Section 1: Floating Navbar ── */

export function LandingNav() {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  if (typeof window !== "undefined") {
    window.addEventListener("scroll", () => {
      setScrolled(window.scrollY > 20);
    }, { passive: true });
  }

  const toggleLocale = () => setLocale(locale === "ko" ? "en" : "ko");

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
      style={{
        backgroundColor: scrolled ? "rgba(255,255,255,0.85)" : "transparent",
        backdropFilter: scrolled ? "blur(12px)" : "none",
        boxShadow: scrolled ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
      }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#0b6bcb] text-white">
            <Brain size={18} weight="bold" />
          </div>
          <span className="text-lg font-bold text-slate-900">NeuroHub</span>
        </Link>

        <div className="hidden items-center gap-4 md:flex">
          <button
            onClick={toggleLocale}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
          >
            <Globe size={16} />
            {locale === "ko" ? "EN" : "KO"}
          </button>
          <Link
            href="/login"
            className="text-sm font-medium text-slate-600 transition hover:text-slate-900"
          >
            {t("landing.ctaLogin")}
          </Link>
          <MovingBorder
            as="a"
            containerClassName="rounded-full"
            borderRadius="9999px"
            className="bg-white text-[#0b6bcb] text-sm font-semibold"
            {...{ href: "/register" } as any}
          >
            {t("landing.ctaStart")}
          </MovingBorder>
        </div>

        <button
          className="flex items-center justify-center rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 md:hidden"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? t("landing.menuClose") : t("landing.menuOpen")}
        >
          {menuOpen ? <X size={22} weight="bold" /> : <List size={22} weight="bold" />}
        </button>
      </div>

      {menuOpen && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="border-t border-slate-100 bg-white px-6 py-4 md:hidden"
        >
          <div className="flex flex-col gap-3">
            <button
              onClick={toggleLocale}
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              <Globe size={16} />
              {locale === "ko" ? "English" : "한국어"}
            </button>
            <Link href="/login" className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50" onClick={() => setMenuOpen(false)}>
              {t("landing.ctaLogin")}
            </Link>
            <Link href="/register" className="rounded-lg bg-[#0b6bcb] px-3 py-2 text-center text-sm font-semibold text-white" onClick={() => setMenuOpen(false)}>
              {t("landing.ctaStart")}
            </Link>
          </div>
        </motion.div>
      )}
    </nav>
  );
}

/* ── Section 2: Hero with Aurora Background ── */

export function HeroSection() {
  const t = useT();

  return (
    <AuroraBackground className="min-h-[90vh] pt-24 pb-16">
      <div className="mx-auto max-w-7xl px-6">
        <div className="flex flex-col items-center gap-12 lg:flex-row lg:items-center lg:gap-16">
          <div className="flex-1 text-center lg:text-left">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="mb-6 inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-4 py-1.5 text-sm font-medium text-[#0b6bcb]"
            >
              {t("landing.badge")}
            </motion.div>

            <TextGenerateEffect
              words={t("landing.heroTitle")}
              className="text-4xl leading-tight text-slate-900 md:text-5xl lg:text-6xl"
            />

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.2, duration: 0.8 }}
              className="mt-6 whitespace-pre-line text-lg leading-relaxed text-slate-700 md:text-xl"
            >
              {t("landing.heroSubtitle")}
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.6, duration: 0.6 }}
              className="mt-8 flex flex-col gap-4 sm:flex-row sm:justify-center lg:justify-start"
            >
              <MovingBorder
                as="a"
                containerClassName="rounded-full"
                borderRadius="9999px"
                className="bg-[#0b6bcb] text-white text-base font-semibold px-8"
                {...{ href: "/register" } as any}
              >
                {t("landing.ctaStart")}
              </MovingBorder>
              <a
                href="#features"
                className="flex items-center justify-center rounded-full border border-slate-300 bg-white px-8 py-3 text-base font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
              >
                {t("landing.ctaLearnMore")}
              </a>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.8, duration: 1 }}
            className="flex-1 hidden lg:flex justify-center"
          >
            <BrainNetwork className="w-full max-w-[400px]" />
          </motion.div>
        </div>
      </div>
    </AuroraBackground>
  );
}

/* ── Section 3: Stats Bar ── */

function CountUp({ end, suffix }: { end: number; suffix: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true });
  const [count, setCount] = useState(0);

  if (isInView && count === 0) {
    let current = 0;
    const step = Math.max(1, Math.floor(end / 40));
    const interval = setInterval(() => {
      current += step;
      if (current >= end) {
        current = end;
        clearInterval(interval);
      }
      setCount(current);
    }, 30);
  }

  return (
    <span ref={ref} className="text-3xl font-bold text-[#0b6bcb] md:text-4xl">
      {count.toLocaleString()}{suffix}
    </span>
  );
}

export function StatsBar() {
  const t = useT();

  const stats = [
    { value: 21, suffix: "+", label: t("landing.statTechniques") },
    { value: 4, suffix: "", label: t("landing.statContainers") },
    { value: 7, suffix: "", label: t("landing.statServices") },
    { value: 10001, suffix: "+", label: t("landing.statInstances") },
  ];

  return (
    <section className="relative border-y border-slate-200 bg-white py-12 overflow-hidden">
      <GradientMesh variant="blue" />
      <div className="relative z-10 mx-auto grid max-w-7xl grid-cols-2 gap-8 px-6 md:grid-cols-4">
        {stats.map((stat) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center"
          >
            <CountUp end={stat.value} suffix={stat.suffix} />
            <p className="mt-2 text-sm font-medium text-slate-700">{stat.label}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

/* ── Section 4: Key Features — Bento Grid ── */

export function FeaturesSection() {
  const t = useT();

  const features = [
    {
      title: t("landing.featurePipeline"),
      description: t("landing.featurePipelineDesc"),
      header: (
        <div className="flex h-36 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 p-4">
          <PipelineFlow className="w-full" />
        </div>
      ),
      className: "md:col-span-2",
    },
    {
      title: t("landing.featureModality"),
      description: t("landing.featureModalityDesc"),
      header: (
        <div className="flex h-36 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-blue-50 to-slate-50 p-2">
          <ModalityWave className="w-full" />
        </div>
      ),
      className: "",
    },
    {
      title: t("landing.featurePreQC"),
      description: t("landing.featurePreQCDesc"),
      header: (
        <div className="flex h-36 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-green-50 to-blue-50 p-2">
          <QualityScan className="w-full max-w-[180px]" />
        </div>
      ),
    },
    {
      title: t("landing.featureFusion"),
      description: t("landing.featureFusionDesc"),
      header: (
        <div className="flex h-36 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-purple-50 to-blue-50 p-2">
          <FusionConvergence className="w-full max-w-[180px]" />
        </div>
      ),
    },
    {
      title: t("landing.featureReport"),
      description: t("landing.featureReportDesc"),
      header: (
        <div className="flex h-36 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-orange-50 to-blue-50 p-2">
          <ReportGenerate className="w-full max-w-[180px]" />
        </div>
      ),
    },
    {
      title: t("landing.featureSecurity"),
      description: t("landing.featureSecurityDesc"),
      header: (
        <div className="flex h-36 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-red-50 to-blue-50 p-2">
          <ShieldSecure className="w-full max-w-[180px]" />
        </div>
      ),
    },
  ];

  return (
    <section id="features" className="relative overflow-hidden bg-slate-50 py-20">
      <GradientMesh variant="blue" />
      <FloatingParticles count={8} />
      <div className="relative z-10 mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-12 text-center"
        >
          <h2 className="text-3xl font-bold text-slate-900 md:text-4xl">
            {t("landing.sectionTitleWhy")}
          </h2>
        </motion.div>

        <BentoGrid className="gap-6">
          {features.map((feature) => (
            <BentoGridItem
              key={feature.title}
              title={feature.title}
              description={feature.description}
              header={feature.header}
              className={feature.className}
            />
          ))}
        </BentoGrid>
      </div>
    </section>
  );
}

/* ── Section 5: How It Works — Futuristic Timeline ── */

export function HowItWorksSection() {
  const t = useT();

  const steps = [
    { num: 1, title: t("landing.stepUpload"), desc: t("landing.stepUploadDesc"), icon: <UploadIcon className="w-20 h-20" /> },
    { num: 2, title: t("landing.stepAnalysis"), desc: t("landing.stepAnalysisDesc"), icon: <AnalysisIcon className="w-20 h-20" /> },
    { num: 3, title: t("landing.stepResults"), desc: t("landing.stepResultsDesc"), icon: <ResultsIcon className="w-20 h-20" /> },
    { num: 4, title: t("landing.stepReport"), desc: t("landing.stepReportDesc"), icon: <ReportDownloadIcon className="w-20 h-20" /> },
  ];

  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-white via-blue-50/30 to-white py-24">
      <GradientMesh variant="indigo" />
      <FloatingParticles count={10} />

      <div className="relative z-10 mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-16 text-center"
        >
          <h2 className="text-3xl font-bold text-slate-900 md:text-4xl">
            {t("landing.sectionHowItWorks")}
          </h2>
        </motion.div>

        {/* Timeline connector line */}
        <div className="relative">
          <div className="absolute left-1/2 top-0 hidden h-full w-px -translate-x-1/2 lg:block">
            <motion.div
              className="h-full w-full bg-gradient-to-b from-transparent via-[#0b6bcb] to-transparent"
              initial={{ scaleY: 0 }}
              whileInView={{ scaleY: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 1.5 }}
              style={{ transformOrigin: "top" }}
            />
          </div>

          <div className="grid gap-12 lg:gap-16">
            {steps.map((step, i) => (
              <motion.div
                key={step.num}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15 }}
                className={`flex flex-col items-center gap-8 lg:flex-row ${i % 2 === 1 ? "lg:flex-row-reverse" : ""}`}
              >
                {/* SVG animation side */}
                <div className="flex-1 flex justify-center">
                  <div className="relative">
                    {/* Glow circle behind icon */}
                    <div
                      className="absolute inset-0 rounded-full opacity-10"
                      style={{
                        background: `radial-gradient(circle, #0b6bcb 0%, transparent 70%)`,
                        transform: "scale(1.5)",
                      }}
                    />
                    <div className="relative rounded-2xl border border-blue-100 bg-white/80 p-6 shadow-lg backdrop-blur-sm">
                      {step.icon}
                    </div>
                  </div>
                </div>

                {/* Center step indicator (desktop) */}
                <div className="hidden lg:flex flex-col items-center">
                  <motion.div
                    className="flex h-12 w-12 items-center justify-center rounded-full bg-[#0b6bcb] text-white font-bold text-lg shadow-lg shadow-blue-200"
                    whileInView={{ scale: [0, 1.1, 1] }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.2, type: "spring" }}
                  >
                    {step.num}
                  </motion.div>
                </div>

                {/* Text side */}
                <div className="flex-1 text-center lg:text-left">
                  <div className="mb-2 text-xs font-bold uppercase tracking-wider text-[#0b6bcb] lg:hidden">
                    {t("landing.stepLabel")} {step.num}
                  </div>
                  <h3 className="mb-3 text-xl font-semibold text-slate-900 md:text-2xl">{step.title}</h3>
                  <p className="text-base leading-relaxed text-slate-600">{step.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ── Section 6: Clinical Services Showcase ── */

export function ClinicalServicesSection() {
  const t = useT();

  const services = [
    {
      title: t("landing.serviceEpilepsy"),
      desc: t("landing.serviceEpilepsyDesc"),
      modalities: ["FDG-PET", "MRI"],
      techniques: 6,
      color: "#3b82f6",
      icon: <EpilepsyIcon className="w-24 h-24" />,
    },
    {
      title: t("landing.serviceDementia"),
      desc: t("landing.serviceDementiaDesc"),
      modalities: ["Amyloid-PET", "MRI"],
      techniques: 5,
      color: "#6366f1",
      icon: <DementiaIcon className="w-24 h-24" />,
    },
    {
      title: t("landing.serviceParkinson"),
      desc: t("landing.serviceParkinsonDesc"),
      modalities: ["DAT-PET", "DTI"],
      techniques: 4,
      color: "#0b6bcb",
      icon: <ParkinsonIcon className="w-24 h-24" />,
    },
    {
      title: t("landing.serviceTumor"),
      desc: t("landing.serviceTumorDesc"),
      modalities: ["MRI"],
      techniques: 3,
      color: "#2563eb",
      icon: <TumorIcon className="w-24 h-24" />,
    },
  ];

  return (
    <section className="relative overflow-hidden py-24" style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%)" }}>
      {/* Animated grid overlay */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.08]" style={{
        backgroundImage: "linear-gradient(rgba(59,130,246,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(59,130,246,0.5) 1px, transparent 1px)",
        backgroundSize: "80px 80px",
      }} />
      <FloatingParticles count={15} />

      <div className="relative z-10 mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-16 text-center"
        >
          <h2 className="text-3xl font-bold text-white md:text-4xl">
            {t("landing.sectionServices")}
          </h2>
        </motion.div>

        <div className="grid gap-6 md:grid-cols-2">
          {services.map((svc, i) => (
            <motion.div
              key={svc.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <CardContainer containerClassName="w-full">
                <CardBody className="w-full rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm transition-all hover:bg-white/10 hover:border-white/20">
                  <CardItem translateZ={40}>
                    <div className="flex items-start gap-5">
                      <div className="flex-shrink-0">
                        {svc.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="mb-3 flex flex-wrap gap-2">
                          {svc.modalities.map((mod) => (
                            <span
                              key={mod}
                              className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
                              style={{
                                backgroundColor: `${svc.color}25`,
                                color: svc.color,
                              }}
                            >
                              {mod}
                            </span>
                          ))}
                          <span className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-medium text-blue-200">
                            {svc.techniques}{t("landing.techniquesCount")}
                          </span>
                        </div>
                        <h3 className="text-xl font-semibold text-white">{svc.title}</h3>
                        <p className="mt-2 text-sm leading-relaxed text-blue-200">{svc.desc}</p>
                      </div>
                    </div>
                  </CardItem>
                </CardBody>
              </CardContainer>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── Section 7: Visionary ── */

export function VisionarySection() {
  const t = useT();

  return (
    <section className="relative overflow-hidden bg-white py-24">
      <GradientMesh variant="blue" />
      <div className="relative z-10 mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-12 text-center"
        >
          <h2 className="text-3xl font-bold text-slate-900 md:text-4xl">
            {t("landing.sectionVisionary")}
          </h2>
          <p className="mt-3 text-lg text-slate-600">
            {t("landing.sectionSubtitleVisionary")}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto max-w-3xl"
        >
          <SpotlightCard className="flex flex-col items-center gap-6 md:flex-row md:items-start md:gap-8">
            <div className="flex-shrink-0">
              <img
                src="/prof-park.png"
                alt={t("landing.visionaryName")}
                width={140}
                height={140}
                className="rounded-2xl object-cover"
              />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-[#0b6bcb]">
                {t("landing.sectionVisionary")}
              </p>
              <h3 className="mt-1 text-2xl font-bold text-slate-900">
                {t("landing.visionaryName")}
              </h3>
              <p className="mt-1 text-sm font-medium text-slate-600">
                {t("landing.visionaryAffiliation")}
              </p>
              <p className="mt-3 text-sm leading-relaxed text-slate-700">
                {t("landing.visionaryBio")}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {[
                  t("landing.visionaryTag1"),
                  t("landing.visionaryTag2"),
                  t("landing.visionaryTag3"),
                  t("landing.visionaryTag4"),
                ].map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-[#0b6bcb]"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </SpotlightCard>
        </motion.div>
      </div>
    </section>
  );
}

/* ── Section 8: CTA Footer with Wavy Background ── */

export function FooterCTA() {
  const t = useT();

  return (
    <section className="relative overflow-hidden py-24" style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0b6bcb 100%)" }}>
      <FloatingParticles count={15} />
      {/* Animated grid */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.06]" style={{
        backgroundImage: "linear-gradient(rgba(147,197,253,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(147,197,253,0.5) 1px, transparent 1px)",
        backgroundSize: "60px 60px",
      }} />

      <div className="relative z-10 flex flex-col items-center text-center px-6">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-3xl font-bold text-white md:text-4xl"
        >
          {t("landing.footerCtaTitle")}
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.15 }}
          className="mt-4 max-w-lg text-lg text-blue-200"
        >
          {t("landing.footerCtaSubtitle")}
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="mt-8"
        >
          <MovingBorder
            as="a"
            containerClassName="rounded-full"
            borderRadius="9999px"
            className="bg-white text-[#0b6bcb] text-base font-semibold px-10"
            {...{ href: "/register" } as any}
          >
            {t("landing.ctaStart")}
          </MovingBorder>
        </motion.div>
      </div>
    </section>
  );
}
