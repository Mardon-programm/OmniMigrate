import { Link } from "react-router-dom";

import { useI18n } from "@/i18n";

type LegalSection = { heading: string; body: string };

const COPY = {
  en: {
    privacy: {
      title: "Privacy Policy",
      updated: "Last updated: 23 November 2026",
      intro:
        "OmniMigrate processes source code and account data to provide automated migration services. This policy explains what we collect, why, and how long we keep it.",
      sections: [
        {
          heading: "Data we process",
          body: "Account details (email, name, organization), uploaded source code, repository metadata, migration job logs, billing status, and usage counters (jobs, files, LLM tokens).",
        },
        {
          heading: "How we use it",
          body: "To run migrations, produce pull requests, enforce the output contract, meter quotas, handle support requests, and improve the service. Source code is used only for the job you submit and is not used to train shared models.",
        },
        {
          heading: "Processors",
          body: "We use Paddle for billing, a Gemini-compatible LLM provider for code transformation, GitHub for repository access and pull requests, and managed PostgreSQL/Redis for storage. Each processor receives only the data required for its function.",
        },
        {
          heading: "Retention",
          body: "Job workspaces and generated diffs are retained for 30 days after a job completes, then deleted. Billing records are retained as required by tax law. You may request earlier deletion by contacting support.",
        },
        {
          heading: "Contact",
          body: "Questions or deletion requests: support@omnimigrate.app",
        },
      ] satisfies LegalSection[],
    },
    terms: {
      title: "Terms of Service",
      updated: "Last updated: 23 November 2026",
      intro:
        "These terms govern your use of OmniMigrate. By creating an account or submitting a migration job you agree to them.",
      sections: [
        {
          heading: "Service",
          body: "OmniMigrate generates candidate migrations and pull requests. You remain responsible for reviewing outputs and for deciding what to merge into your repository.",
        },
        {
          heading: "Acceptable use",
          body: "Do not upload code you are not authorised to process, attempt to abuse quotas, probe the sandbox, or use the service to generate malicious code. We may suspend accounts that violate these rules.",
        },
        {
          heading: "Billing",
          body: "Subscriptions and migration packs are billed through Paddle. Prices are shown at checkout. Unless required by law, fees are non-refundable; contact support for billing errors.",
        },
        {
          heading: "Intellectual property",
          body: "You retain ownership of your source code and of migration outputs generated for you. We retain ownership of the platform, prompts, and migration engine.",
        },
        {
          heading: "Warranty",
          body: "The service is provided on an early-access basis. We aim for high preservation guarantees but do not warrant that every generated diff is fit for production without review.",
        },
      ] satisfies LegalSection[],
    },
    back: "Back to home",
  },
  ru: {
    privacy: {
      title: "Политика конфиденциальности",
      updated: "Обновлено: 23 ноября 2026",
      intro:
        "OmniMigrate обрабатывает исходный код и данные аккаунта для оказания услуг автоматической миграции. Здесь описано, что мы собираем, зачем и как долго храним.",
      sections: [
        {
          heading: "Какие данные мы обрабатываем",
          body: "Данные аккаунта (email, имя, организация), загруженный код, метаданные репозиториев, логи заданий, статус оплаты и счётчики использования (задания, файлы, токены LLM).",
        },
        {
          heading: "Как мы их используем",
          body: "Для выполнения миграции, создания pull request, проверки контракта, учёта квот и поддержки. Код используется только для вашего задания и не применяется для обучения общих моделей.",
        },
        {
          heading: "Обработчики",
          body: "Paddle — биллинг, провайдер Gemini — трансформация кода, GitHub — доступ к репозиторию и PR, управляемые PostgreSQL/Redis — хранение. Каждый получает только необходимые данные.",
        },
        {
          heading: "Хранение",
          body: "Рабочие директории и diff-файлы удаляются через 30 дней после завершения задания. Платёжные записи хранятся в соответствии с налоговым законодательством. Удаление ранее — по запросу на support@omnimigrate.app",
        },
        {
          heading: "Контакты",
          body: "Вопросы и запросы на удаление: support@omnimigrate.app",
        },
      ] satisfies LegalSection[],
    },
    terms: {
      title: "Условия использования",
      updated: "Обновлено: 23 ноября 2026",
      intro:
        "Эти условия регулируют использование OmniMigrate. Создавая аккаунт или отправляя задание, вы с ними соглашаетесь.",
      sections: [
        {
          heading: "Сервис",
          body: "OmniMigrate создаёт кандидатов на миграцию и pull request. Вы самостоятельно проверяете результаты и решаете, что мержить в репозиторий.",
        },
        {
          heading: "Допустимое использование",
          body: "Не загружайте код, на обработку которого у вас нет прав, не обходите квоты, не тестируйте песочницу и не генерируйте вредоносный код. Мы можем приостановить аккаунт при нарушениях.",
        },
        {
          heading: "Оплата",
          body: "Подписки и паки миграций оплачиваются через Paddle. Цены указаны при оформлении. Возврат средств производится по закону или при ошибке биллинга — напишите в поддержку.",
        },
        {
          heading: "Интеллектуальная собственность",
          body: "Код и результаты миграции остаются вашей собственностью. Платформа, промпты и движок миграций остаются нашей собственностью.",
        },
        {
          heading: "Гарантии",
          body: "Сервис предоставляется в режиме раннего доступа. Мы стремимся к сохранению API и логики, но не гарантируем, что каждый diff готов к продакшену без ревью.",
        },
      ] satisfies LegalSection[],
    },
    back: "На главную",
  },
};

function LegalDocument({ kind }: { kind: "privacy" | "terms" }) {
  const { locale } = useI18n();
  const copy = COPY[locale][kind];

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:py-24">
      <p className="text-sm uppercase tracking-widest text-brand-emeraldLight">
        OmniMigrate
      </p>
      <h1 className="mt-3 text-4xl font-bold text-white sm:text-5xl">{copy.title}</h1>
      <p className="mt-2 text-sm text-muted">{copy.updated}</p>
      <p className="mt-8 text-lg leading-relaxed text-text-secondary">{copy.intro}</p>

      <div className="mt-10 space-y-8">
        {copy.sections.map((section) => (
          <section key={section.heading}>
            <h2 className="text-xl font-semibold text-white">{section.heading}</h2>
            <p className="mt-2 leading-relaxed text-text-secondary">{section.body}</p>
          </section>
        ))}
      </div>

      <Link to="/" className="btn-secondary mt-12 inline-flex">
        {COPY[locale].back}
      </Link>
    </div>
  );
}

export function Privacy() {
  return <LegalDocument kind="privacy" />;
}

export function Terms() {
  return <LegalDocument kind="terms" />;
}
