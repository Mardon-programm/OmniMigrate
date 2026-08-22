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
    <div className="card relative mb-6 border border-primary/20 !bg-surface/50">
      <button
        onClick={handleDismiss}
        className="absolute right-3 top-3 rounded-lg p-1 text-muted transition-colors hover:bg-surface2 hover:text-white"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
      <div className="mb-4 flex items-center gap-3">
        <CheckCircle2 className="h-5 w-5 text-primary" />
        <h3 className="text-sm font-semibold text-white">{t("onboard.title")}</h3>
      </div>
      <div className="space-y-3">
        {steps.map((step, i) => (
          <button
            key={i}
            onClick={() => navigate(step.link)}
            className="flex w-full items-center gap-3 rounded-lg border border-border/50 bg-surface/60 p-3 text-left transition-all hover:border-primary/40 hover:bg-surface2"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <step.icon className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-white">{t(step.titleKey)}</p>
              <p className="text-xs text-muted">{t(step.descKey)}</p>
            </div>
            <ArrowRight className="h-4 w-4 text-muted" />
          </button>
        ))}
      </div>
    </div>
  );
}
