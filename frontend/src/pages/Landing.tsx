import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Code2,
  Cpu,
  FileDiff,
  GitBranch,
  Layers,
  Rocket,
  Shield,
  Sparkles,
  TerminalSquare,
  Zap,
} from "lucide-react";

import { useI18n } from "@/i18n";

const MARKETING_URL = import.meta.env.VITE_MARKETING_URL || "https://omni-migrate-company.vercel.app";

const FEATURES = [
  {
    icon: FileDiff,
    title: "landing.features.astTitle",
    desc: "landing.features.astDesc",
  },
  {
    icon: Sparkles,
    title: "landing.features.llmTitle",
    desc: "landing.features.llmDesc",
  },
  {
    icon: Cpu,
    title: "landing.features.sandboxTitle",
    desc: "landing.features.sandboxDesc",
  },
  {
    icon: Shield,
    title: "landing.features.securityTitle",
    desc: "landing.features.securityDesc",
  },
  {
    icon: GitBranch,
    title: "landing.features.gitTitle",
    desc: "landing.features.gitDesc",
  },
  {
    icon: Zap,
    title: "landing.features.autonomousTitle",
    desc: "landing.features.autonomousDesc",
  },
];

const PRICING = [
  {
    name: "landing.pricing.starter",
    price: "$19",
    period: "/month",
    description: "landing.pricing.starterDesc",
    features: [
      "landing.pricing.feat1",
      "landing.pricing.feat2",
      "landing.pricing.feat3",
      "landing.pricing.feat4",
    ],
    cta: "landing.pricing.getEarlyAccess",
    popular: false,
  },
  {
    name: "landing.pricing.pro",
    price: "$79",
    period: "/month",
    description: "landing.pricing.proDesc",
    features: [
      "landing.pricing.feat1",
      "landing.pricing.feat2",
      "landing.pricing.feat3",
      "landing.pricing.feat4",
      "landing.pricing.feat5",
      "landing.pricing.feat6",
    ],
    cta: "landing.pricing.getEarlyAccess",
    popular: true,
  },
  {
    name: "landing.pricing.enterprise",
    price: "Custom",
    period: "",
    description: "landing.pricing.enterpriseDesc",
    features: [
      "landing.pricing.feat1",
      "landing.pricing.feat2",
      "landing.pricing.feat3",
      "landing.pricing.feat4",
      "landing.pricing.feat5",
      "landing.pricing.feat6",
      "landing.pricing.feat7",
    ],
    cta: "landing.pricing.contactSales",
    popular: false,
  },
];

const DEMO_CODE = `def fetch_users_with_posts():
    users = User.query.all()
    for user in users:
        print(user.posts)  # N+1 query!`;

const DEMO_RESULT = `def fetch_users_with_posts():
    users = User.query.options(
        joinedload(User.posts)
    ).all()
    for user in users:
        print(user.posts)  # Single query!`;

export function Landing() {
  const { t } = useI18n();

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Navigation */}
      <header className="sticky top-0 z-50 border-b border-border-primary bg-bg-secondary/80 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <Link to="/" className="flex items-center gap-2" aria-label="OmniMigrate">
              <img src="/logo.png" alt="OmniMigrate" className="h-8 w-8 rounded-xl" />
              <span className="text-heading-md font-bold text-text-primary">OmniMigrate</span>
            </Link>
            <nav className="hidden md:flex items-center gap-6">
              <Link to="#features" className="text-body-sm text-text-secondary hover:text-text-primary transition-colors">
                {t("landing.nav.features")}
              </Link>
              <Link to="#pricing" className="text-body-sm text-text-secondary hover:text-text-primary transition-colors">
                {t("landing.nav.pricing")}
              </Link>
              <Link to="#demo" className="text-body-sm text-text-secondary hover:text-text-primary transition-colors">
                {t("landing.nav.demo")}
              </Link>
              <Link to="/docs" className="text-body-sm text-text-secondary hover:text-text-primary transition-colors">
                {t("landing.nav.docs")}
              </Link>
            </nav>
            <div className="flex items-center gap-3">
              <Link to="/login" className="btn-ghost btn-sm hidden sm:inline-flex">
                {t("landing.nav.signIn")}
              </Link>
              <a
                href={`${MARKETING_URL}/auth?plan=pro`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary btn-sm hidden sm:inline-flex"
              >
                {t("landing.nav.getStarted")}
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden py-20 sm:py-32">
        <div className="absolute inset-0 bg-mesh-gradient" />
        <div className="absolute inset-0 bg-noise opacity-[0.03]" />
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative">
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 rounded-full bg-brand-emerald/10 border border-brand-emerald/20 px-4 py-1.5 mb-6 text-caption font-medium text-brand-emeraldLight">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inset-0 rounded-full bg-brand-emerald animate-ping opacity-75" />
                <span className="relative block h-1.5 w-1.5 rounded-full bg-brand-emerald" />
              </span>
              {t("landing.hero.badge")}
            </div>
            <h1 className="text-display-lg font-extrabold tracking-tight text-text-primary mb-6">
              {t("landing.hero.titlePre")}
              <br />
              <span className="text-gradient-emerald">{t("landing.hero.titleAccent")}</span>
            </h1>
            <p className="text-body-lg text-text-secondary max-w-2xl mx-auto mb-10">
              {t("landing.hero.subtitle")}
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
              <a
                href={`${MARKETING_URL}/auth?plan=pro`}
                className="btn-primary btn-lg w-full sm:w-auto"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Rocket className="h-5 w-5" />
                {t("landing.hero.ctaPrimary")}
              </a>
              <Link to="#demo" className="btn-secondary btn-lg w-full sm:w-auto">
                <Code2 className="h-5 w-5" />
                {t("landing.hero.ctaSecondary")}
              </Link>
            </div>
            <div className="flex items-center justify-center gap-8 text-caption text-text-tertiary">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-success-text" />
                {t("landing.hero.trust1")}
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-success-text" />
                {t("landing.hero.trust2")}
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-success-text" />
                {t("landing.hero.trust3")}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Demo */}
      <section id="demo" className="py-20 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-display-md font-extrabold tracking-tight text-text-primary mb-4">
              {t("landing.landingDemo.title")}
            </h2>
            <p className="text-body-lg text-text-secondary max-w-2xl mx-auto">
              {t("landing.landingDemo.subtitle")}
            </p>
          </div>
          <div className="grid lg:grid-cols-2 gap-8">
            <div className="card">
              <div className="code-block__header">
                <span className="code-block__title flex items-center gap-2 font-mono">
                  <TerminalSquare className="h-3.5 w-3.5 text-brand-emerald/70" />
                  {t("landing.landingDemo.before")}
                </span>
                <span className="badge-warning">{t("landing.landingDemo.issues")}</span>
              </div>
              <pre className="code-block overflow-auto p-4">
                <code className="text-danger-text">{DEMO_CODE}</code>
              </pre>
              <ul className="p-4 space-y-2 text-caption text-text-tertiary border-t border-border-primary">
                <li className="flex items-center gap-2 text-danger-text">
                  <span className="h-1.5 w-1.5 rounded-full bg-danger" />
                  N+1 query detected
                </li>
                <li className="flex items-center gap-2 text-warning-text">
                  <span className="h-1.5 w-1.5 rounded-full bg-warning" />
                  Missing eager loading
                </li>
              </ul>
            </div>
            <div className="card">
              <div className="code-block__header">
                <span className="code-block__title flex items-center gap-2 font-mono">
                  <TerminalSquare className="h-3.5 w-3.5 text-brand-emerald/70" />
                  {t("landing.landingDemo.after")}
                </span>
                <span className="badge-success">{t("landing.landingDemo.fixed")}</span>
              </div>
              <pre className="code-block overflow-auto p-4">
                <code className="text-success-text">{DEMO_RESULT}</code>
              </pre>
              <ul className="p-4 space-y-2 text-caption text-text-tertiary border-t border-border-primary">
                <li className="flex items-center gap-2 text-success-text">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  joinedload() added
                </li>
                <li className="flex items-center gap-2 text-success-text">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Single optimized query
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 sm:py-24 bg-bg-secondary/50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-display-md font-extrabold tracking-tight text-text-primary mb-4">
              {t("landing.features.title")}
            </h2>
            <p className="text-body-lg text-text-secondary max-w-2xl mx-auto">
              {t("landing.features.subtitle")}
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((feature, i) => (
              <div key={i} className="card card-hover group p-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-emerald/10 border border-brand-emerald/20 text-brand-emerald mb-4 group-hover:scale-105 transition-transform">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="text-heading-sm font-semibold text-text-primary mb-2">
                  {t(feature.title)}
                </h3>
                <p className="text-body-sm text-text-secondary">
                  {t(feature.desc)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-20 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-display-md font-extrabold tracking-tight text-text-primary mb-4">
              {t("landing.pricing.title")}
            </h2>
            <p className="text-body-lg text-text-secondary max-w-2xl mx-auto">
              {t("landing.pricing.subtitle")}
            </p>
          </div>
          <div className="grid lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {PRICING.map((plan, i) => (
              <div
                key={i}
                className={`card p-6 relative ${
                  plan.popular
                    ? "border-brand-emerald/50 shadow-[0_0_0_1px_rgb(16_185_129_/_0.3)]"
                    : ""
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="badge-primary">{t("landing.pricing.popular")}</span>
                  </div>
                )}
                <h3 className="text-heading-md font-semibold text-text-primary mb-1">
                  {t(plan.name)}
                </h3>
                <p className="text-caption text-text-tertiary mb-6">{t(plan.description)}</p>
                <div className="mb-6">
                  <span className="text-display-lg font-extrabold text-text-primary">
                    {plan.price}
                  </span>
                  <span className="text-body-sm text-text-tertiary">{plan.period}</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feat, fi) => (
                    <li key={fi} className="flex items-start gap-3">
                      <CheckCircle2 className="h-5 w-5 text-success-text shrink-0 mt-0.5" />
                      <span className="text-body-sm text-text-secondary">{t(feat)}</span>
                    </li>
                  ))}
                </ul>
                <a
                  href={`${MARKETING_URL}/auth?plan=${plan.name === "Professional" ? "pro" : plan.name === "Enterprise" ? "enterprise" : "starter"}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`btn-primary w-full ${
                    plan.popular ? "" : "bg-bg-tertiary border border-border-primary text-text-primary hover:bg-brand-emerald/10 hover:border-brand-emerald/30"
                  }`}
                >
                  {t(plan.cta)}
                  <ArrowRight className="h-4 w-4" />
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 sm:py-24 bg-brand-gradient">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-display-md font-extrabold tracking-tight text-white mb-4">
            {t("landing.cta.title")}
          </h2>
          <p className="text-body-lg text-white/80 max-w-2xl mx-auto mb-8">
            {t("landing.cta.subtitle")}
          </p>
          <a
            href={`${MARKETING_URL}/auth?plan=pro`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-accent btn-lg px-8"
          >
            {t("landing.cta.button")}
            <ArrowRight className="h-5 w-5" />
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border-primary bg-bg-secondary py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
            <div className="lg:col-span-2">
              <Link to="/" className="flex items-center gap-2 mb-4">
                <img src="/logo.png" alt="OmniMigrate" className="h-8 w-8 rounded-xl" />
                <span className="text-heading-md font-bold text-text-primary">OmniMigrate</span>
              </Link>
              <p className="text-body-sm text-text-secondary max-w-xs mb-6">
                {t("landing.footer.description")}
              </p>
              <div className="flex gap-4">
                <a href="https://github.com" target="_blank" rel="noopener" className="text-text-tertiary hover:text-brand-emeraldLight transition-colors" aria-label="GitHub">
                  <TerminalSquare className="h-5 w-5" />
                </a>
                <a href="https://twitter.com" target="_blank" rel="noopener" className="text-text-tertiary hover:text-brand-emeraldLight transition-colors" aria-label="Twitter">
                  <Sparkles className="h-5 w-5" />
                </a>
                <a href="https://linkedin.com" target="_blank" rel="noopener" className="text-text-tertiary hover:text-brand-emeraldLight transition-colors" aria-label="LinkedIn">
                  <Layers className="h-5 w-5" />
                </a>
              </div>
            </div>
            <div>
              <h4 className="font-semibold text-text-primary mb-4">{t("landing.footer.product")}</h4>
              <ul className="space-y-2 text-body-sm text-text-secondary">
                <li><Link to="#features" className="hover:text-brand-emeraldLight transition-colors">{t("landing.nav.features")}</Link></li>
                <li><Link to="#pricing" className="hover:text-brand-emeraldLight transition-colors">{t("landing.nav.pricing")}</Link></li>
                <li><Link to="/docs" className="hover:text-brand-emeraldLight transition-colors">{t("landing.nav.docs")}</Link></li>
                <li><Link to="/changelog" className="hover:text-brand-emeraldLight transition-colors">{t("landing.footer.changelog")}</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-text-primary mb-4">{t("landing.footer.company")}</h4>
              <ul className="space-y-2 text-body-sm text-text-secondary">
                <li><Link to="/about" className="hover:text-brand-emeraldLight transition-colors">{t("landing.footer.about")}</Link></li>
                <li><Link to="/blog" className="hover:text-brand-emeraldLight transition-colors">{t("landing.footer.blog")}</Link></li>
                <li><Link to="/careers" className="hover:text-brand-emeraldLight transition-colors">{t("landing.footer.careers")}</Link></li>
                <li><Link to="/contact" className="hover:text-brand-emeraldLight transition-colors">{t("landing.footer.contact")}</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-text-primary mb-4">{t("landing.footer.legal")}</h4>
              <ul className="space-y-2 text-body-sm text-text-secondary">
                <li><Link to="/privacy" className="hover:text-brand-emeraldLight transition-colors">{t("landing.footer.privacy")}</Link></li>
                <li><Link to="/terms" className="hover:text-brand-emeraldLight transition-colors">{t("landing.footer.terms")}</Link></li>
                <li><Link to="/security" className="hover:text-brand-emeraldLight transition-colors">{t("landing.footer.security")}</Link></li>
                <li><Link to="/cookies" className="hover:text-brand-emeraldLight transition-colors">{t("landing.footer.cookies")}</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-border-primary pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-caption text-text-tertiary">
              {t("landing.footer.copyright")}
            </p>
            <div className="flex items-center gap-4 text-caption text-text-tertiary">
              <span>{t("landing.footer.madeWith")}</span>
              <span className="text-danger">♥</span>
              <span>{t("landing.footer.forDevelopers")}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}