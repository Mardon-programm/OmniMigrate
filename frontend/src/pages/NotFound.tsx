import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRightLeft } from "lucide-react";

import { useI18n } from "@/i18n";

export function NotFound() {
  const { t } = useI18n();
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-gradient shadow-glow">
        <ArrowRightLeft className="h-8 w-8 text-white" />
      </div>
      <div>
        <h1 className="text-4xl font-bold text-white">{t("notFound.title")}</h1>
        <p className="mt-2 text-muted">{t("notFound.subtitle")}</p>
      </div>
      <Link to="/" className="btn-primary">
        <ArrowLeft className="h-4 w-4" />
        {t("notFound.back")}
      </Link>
    </div>
  );
}
