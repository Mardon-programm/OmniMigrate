import { useState } from "react";
import { ArrowRight, Code2, FileDiff } from "lucide-react";
import { Link } from "react-router-dom";

import { CodeBlock } from "@/components/CodeBlock";
import { DiffViewer } from "@/components/DiffViewer";
import { Spinner } from "@/components/Spinner";
import { useToast } from "@/context/ToastContext";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";

const DEMO_EXAMPLES = [
  {
    id: "n1",
    title: "N+1 Query Fix",
    language: "python",
    code: `def get_users_with_posts():
    users = User.query.all()
    for user in users:
        print(user.posts)  # N+1 query!`,
    description: "Detects N+1 pattern and adds joinedload()",
  },
  {
    id: "py2",
    title: "Python 2 → 3 Migration",
    language: "python",
    code: `import urllib2
from StringIO import StringIO

def fetch_data():
    return urllib2.urlopen("http://api.example.com").read()`,
    description: "Modernizes Python 2 imports and syntax",
  },
  {
    id: "sec",
    title: "Security Fixes",
    language: "python",
    code: `import subprocess

def run_user_cmd(cmd):
    # Shell injection vulnerability!
    return subprocess.check_output(cmd, shell=True)`,
    description: "Fixes shell injection and unsafe patterns",
  },
];

export function Demo() {
  const { t } = useI18n();
  const toast = useToast();
  const [selectedExample, setSelectedExample] = useState(DEMO_EXAMPLES[0]);
  const [code, setCode] = useState(DEMO_EXAMPLES[0].code);
  const [filename, setFilename] = useState("example.py");
  const [analyzing, setAnalyzing] = useState(false);
  const [diff, setDiff] = useState<string | null>(null);
  const [output, setOutput] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"diff" | "output">("diff");

  const handleAnalyze = async () => {
    if (!code.trim()) {
      toast.warning(t("demo.needCode"));
      return;
    }
    setAnalyzing(true);
    setDiff(null);
    setOutput(null);
    setError(null);
    try {
      const result = await api.analyze(code, filename);
      if (!result.success) {
        setError(result.parse_error || t("demo.analysisFailed"));
      } else {
        const job = await api.submitJob({
          project_id: 0, // Demo project
          title: `Demo: ${selectedExample.title}`,
          input_code: code,
          priority: "urgent",
        });
        // Poll for result
        let attempts = 0;
        while (attempts < 30) {
          await new Promise((r) => setTimeout(r, 2000));
          const status = await api.getJobStatus(job.id);
          if (status.status === "completed") {
            const fresh = await api.getJob(job.id);
            setDiff(fresh.diff || "");
            setOutput(fresh.output_code || "");
            break;
          } else if (status.status === "failed") {
            setError(t("demo.migrationFailed"));
            break;
          }
          attempts++;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("demo.error"));
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">{t("demo.title")}</h1>
        <p className="page-subtitle max-w-2xl">{t("demo.subtitle")}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="card p-6 space-y-6">
            <div>
              <h2 className="text-heading-md font-semibold text-text-primary mb-4">
                {t("demo.tryIt")}
              </h2>
              <div className="flex gap-2 mb-4 flex-wrap">
                {DEMO_EXAMPLES.map((ex) => (
                  <button
                    key={ex.id}
                    onClick={() => {
                      setSelectedExample(ex);
                      setCode(ex.code);
                      setFilename(ex.id === "py2" ? "legacy.py" : "example.py");
                      setDiff(null);
                      setOutput(null);
                    }}
                    className={`btn-sm px-3 py-1.5 rounded-lg transition-all ${
                      selectedExample.id === ex.id
                        ? "btn-primary"
                        : "btn-secondary"
                    }`}
                  >
                    {ex.title}
                  </button>
                ))}
              </div>

              <div className="form-group">
                <label className="label" htmlFor="demo-filename">
                  {t("demo.filename")}
                </label>
                <input
                  id="demo-filename"
                  className="input max-w-xs font-mono text-code"
                  value={filename}
                  onChange={(e) => setFilename(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="label" htmlFor="demo-code">
                  {t("demo.yourCode")}
                </label>
                <textarea
                  id="demo-code"
                  className="textarea min-h-[300px]"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder={t("demo.codePlaceholder")}
                  spellCheck={false}
                />
              </div>

              <button
                onClick={handleAnalyze}
                disabled={analyzing || !code.trim()}
                className="btn-primary w-full sm:w-auto"
              >
                {analyzing ? (
                  <>
                    <Spinner size="sm" />
                    {t("demo.analyzing")}
                  </>
                ) : (
                  <>
                    <Code2 className="h-4 w-4" />
                    {t("demo.runMigration")}
                  </>
                )}
              </button>

              {error && (
                <div className="rounded-xl border border-danger-border bg-danger-bg p-4 text-body-sm text-danger-text">
                  <p className="font-medium">{t("demo.error")}</p>
                  <p className="mt-1 font-mono text-code">{error}</p>
                </div>
              )}
            </div>

            {(diff || output) && (
              <div className="border-t border-border-primary pt-6">
                <div className="tabs mb-4" role="tablist">
                  <button
                    onClick={() => setTab("diff")}
                    role="tab"
                    aria-selected={tab === "diff"}
                    className={`tab ${tab === "diff" ? "tab-active" : ""}`}
                  >
                    <FileDiff className="h-4 w-4" />
                    {t("demo.diffTab")}
                  </button>
                  <button
                    onClick={() => setTab("output")}
                    role="tab"
                    aria-selected={tab === "output"}
                    className={`tab ${tab === "output" ? "tab-active" : ""}`}
                  >
                    <Code2 className="h-4 w-4" />
                    {t("demo.outputTab")}
                  </button>
                </div>

                {tab === "diff" && diff && <DiffViewer diff={diff} />}
                {tab === "output" && output && (
                  <CodeBlock code={output} title={t("demo.outputTab")} />
                )}
                {tab === "diff" && !diff && (
                  <div className="card flex items-center justify-center py-12 text-body-sm text-text-tertiary">
                    {t("demo.noDiff")}
                  </div>
                )}
                {tab === "output" && !output && (
                  <div className="card flex items-center justify-center py-12 text-body-sm text-text-tertiary">
                    {t("demo.noOutput")}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="card p-6">
            <h3 className="text-heading-sm font-semibold text-text-primary mb-4">
              {t("demo.examples")}
            </h3>
            <ul className="space-y-3">
              {DEMO_EXAMPLES.map((ex) => (
                <li
                  key={ex.id}
                  className={`p-3 rounded-lg transition-colors cursor-pointer ${
                    selectedExample.id === ex.id
                      ? "bg-brand-emerald/10 border border-brand-emerald/20"
                      : "hover:bg-bg-tertiary/50"
                  }`}
                  onClick={() => {
                    setSelectedExample(ex);
                    setCode(ex.code);
                    setFilename(ex.id === "py2" ? "legacy.py" : "example.py");
                  }}
                >
                  <p className="font-medium text-text-primary">{ex.title}</p>
                  <p className="text-caption text-text-tertiary mt-1">{ex.description}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="card p-6">
            <h3 className="text-heading-sm font-semibold text-text-primary mb-4">
              {t("demo.howItWorks")}
            </h3>
            <ol className="space-y-3 text-body-sm text-text-secondary">
              {[
                "Paste legacy code or choose an example",
                "AST analyzer (LibCST) detects patterns",
                "AI refactors with strict prompts",
                "Sandbox verifies the result compiles",
                "Self-healing fixes any errors (max 3 attempts)",
                "Unified diff + metrics returned",
              ].map((step, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="flex-shrink-0 flex h-6 w-6 items-center justify-center rounded-full bg-brand-emerald/10 text-brand-emerald font-mono text-caption font-medium">
                    {i + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>

          <Link to="/register" className="card p-6 text-center">
            <h3 className="text-heading-sm font-semibold text-text-primary mb-2">
              {t("demo.readyToStart")}
            </h3>
            <p className="text-body-sm text-text-secondary mb-4">
              {t("demo.createAccount")}
            </p>
            <button className="btn-primary">
              <ArrowRight className="h-4 w-4" />
              {t("demo.getStartedFree")}
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}