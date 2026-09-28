import { useEffect, useState } from "react";
import { X, User, Phone, Car, FileText, ShieldAlert, Fingerprint, MapPin } from "lucide-react";
import { api, authHeaders } from "../api/client";
import type { components } from "../api/schema";
import { Badge } from "./ui/Badge";
import { ConfidenceBar } from "./ui/ConfidenceBar";

type Dossier = components["schemas"]["SuspectDossierOut"];

interface SuspectSidePanelProps {
  suspectId: number | null;
  onClose: () => void;
}

function Field({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-2.5">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">{label}</p>
        <p className="mt-0.5 text-sm font-medium text-slate-800 dark:text-slate-200">{value}</p>
      </div>
    </div>
  );
}

export default function SuspectSidePanel({ suspectId, onClose }: SuspectSidePanelProps) {
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isOpen = suspectId !== null;

  useEffect(() => {
    if (suspectId === null) return;
    setError(null);
    setDossier(null);
    api
      .GET("/suspects/{suspect_id}", { params: { path: { suspect_id: suspectId }, header: authHeaders() } })
      .then(({ data, error: err }) => {
        if (err) {
          setError(JSON.stringify(err));
          return;
        }
        if (data) setDossier(data);
      });
  }, [suspectId]);

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-slate-900/30 backdrop-blur-[2px] transition-opacity duration-300 dark:bg-black/50 ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      {/* Panel */}
      <aside
        className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-md transform flex-col border-l border-slate-200 bg-white shadow-2xl transition-transform duration-300 ease-out dark:border-slate-800 dark:bg-slate-900 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <Fingerprint className="h-4 w-4" />
            </div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Suspect Dossier</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {error && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
              Error: {error}
            </div>
          )}

          {!error && !dossier && (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
              ))}
            </div>
          )}

          {dossier && (
            <>
              <div className="divide-y divide-slate-50 dark:divide-slate-800/60">
                <Field
                  icon={<User className="h-4 w-4" />}
                  label="Name"
                  value={dossier.name ?? <span className="italic text-slate-400 dark:text-slate-500">Unnamed — identified by identifiers/description only</span>}
                />
                <Field icon={<User className="h-4 w-4" />} label="Aliases" value={dossier.aliases.length ? dossier.aliases.join(", ") : "—"} />
                <Field
                  icon={<Phone className="h-4 w-4" />}
                  label="Phone Numbers"
                  value={dossier.phone_numbers.length ? <span className="font-mono">{dossier.phone_numbers.join(", ")}</span> : "—"}
                />
                <Field
                  icon={<Car className="h-4 w-4" />}
                  label="Vehicle Numbers"
                  value={dossier.vehicle_numbers.length ? <span className="font-mono">{dossier.vehicle_numbers.join(", ")}</span> : "—"}
                />
                <Field icon={<Fingerprint className="h-4 w-4" />} label="Physical Description" value={dossier.physical_description ?? "—"} />
                <Field
                  icon={<FileText className="h-4 w-4" />}
                  label="Associated FIR IDs"
                  value={dossier.associated_fir_ids.join(", ")}
                />
              </div>

              <div className="mt-6">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                  <ShieldAlert className="h-4 w-4" /> Cluster / Syndicate Link
                </h3>

                {dossier.cluster ? (
                  <div
                    className={`rounded-xl border p-4 ${
                      dossier.cluster.syndicate_flag
                        ? "border-red-200 bg-red-50/60 dark:border-red-500/30 dark:bg-red-500/[0.06]"
                        : "border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/40"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <ConfidenceBar value={dossier.cluster.confidence_score} />
                      {dossier.cluster.syndicate_flag ? (
                        <Badge tone="red">SYNDICATE</Badge>
                      ) : (
                        <Badge tone="slate">Lead only</Badge>
                      )}
                    </div>
                    <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                      <MapPin className="h-3 w-3" /> {dossier.cluster.districts_involved.join(", ")}
                    </p>
                    <ul className="mt-3 space-y-1.5 border-t border-slate-200/70 pt-3 text-xs text-slate-600 dark:border-slate-700/60 dark:text-slate-400">
                      {dossier.cluster.match_reasons.map((r, i) => (
                        <li key={i} className="flex gap-1.5">
                          <span className="text-slate-300 dark:text-slate-600">&bull;</span>
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Not part of any repeat-offender cluster — no other FIR currently links to this suspect.
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
