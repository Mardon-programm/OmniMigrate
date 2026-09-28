import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  GitBranch,
  FileCode2,
  Zap,
  X,
} from "lucide-react";
import { useI18n } from "@/i18n";

const STORAGE_KEY = "omnimigrate_onboarded";

interface Step {
  icon: typeof ArrowRight;
  titleKey: string;
  descKey: string;
  link: string;
  linkLabel: string;
}

export function OnboardingChecklist() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setDismissed(localStorage.getItem(STORAGE_KEY) === "true");
  }, []);

  if (dismissed) return null;

  const steps: Step[] = [
    {
      icon: FileCode2,
      titleKey: "onboard.step1Title",
      descKey: "onboard.step1Desc",
      link: "/projects",
      linkLabel: "onboard.step1Link",
    },
    {
      icon: GitBranch,
      titleKey: "onboard.step2Title",
      descKey: "onboard.step2Desc",
      link: "/upload",
      linkLabel: "onboard.step2Link",
    },
    {
      icon: Zap,
      titleKey: "onboard.step3Title",
      descKey: "onboard.step3Desc",
      link: "/autonomous",
      linkLabel: "onboard.step3Link",
    },
  ];

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setDismissed(true);
  };

  return (
    <div className="card border-brand-emerald/20 bg-brand-emerald/5">
      <button
        onClick={handleDismiss}
        className="absolute right-3 top-3 btn-ghost btn-icon-sm"
        aria-label={t("onboard.dismiss")}
      >
        <X className="h-4 w-4" />
      </button>
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-emerald/10">
          <CheckCircle2 className="h-5 w-5 text-brand-emerald" />
        </div>
        <h3 className="text-heading-sm font-semibold text-text-primary">{t("onboard.title")}</h3>
      </div>
      <div className="space-y-2">
        {steps.map((step, i) => (
          <button
            key={i}
            onClick={() => navigate(step.link)}
            className="card-interactive w-full p-4"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-emerald/10">
                <step.icon className="h-4 w-4 text-brand-emerald" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-text-primary">{t(step.titleKey)}</p>
                <p className="text-caption text-text-tertiary">{t(step.descKey)}</p>
              </div>
              <ArrowRight className="h-4 w-4 text-text-tertiary shrink-0" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}