/** Typed mirror of the Python genome API (dna/server.py + genome_ops.py). */

export interface Owner {
  person: string;
  person_id: string;
  weight: number;
}

export interface Risk {
  class: "knowledge_concentration" | "bottleneck" | string;
  score: number;
  note: string;
  evidence: string[];
}

export interface Era {
  label: string;
  start: string | null;
  end: string | null;
  index: number;
}

export interface Dependency {
  on: string;
  mechanism: string | null;
  since: string | null;
  evidence: string[];
}

export interface Profile {
  entity: string;
  id: string;
  kind: string;
  repo: string | null;
  dir: string | null;
  languages: Record<string, number>;
  born: string | null;
  born_commit?: string;
  born_msg?: string;
  eras: Era[];
  dependencies: Dependency[];
  dependents: string[];
  co_changes_with: { service: string; times: number }[];
  knowledge: { effective_owners: number; top: Owner[] };
  risks: Risk[];
  stats: { lifetime_commits: number };
}

export interface GraphNode {
  id: string;
  name: string;
  kind: string;
  born: string | null;
}

export interface GraphEdge {
  src: string;
  dst: string;
  since: string | null;
}

export interface GraphAt {
  at: string;
  services: GraphNode[];
  dependencies: GraphEdge[];
}

export interface DiffResult {
  from: string;
  to: string;
  services_added: { id: string; cause: string | null }[];
  services_removed: string[];
  dependencies_added: string[];
  dependencies_removed: string[];
}

export interface BusFactorImpact {
  service: string;
  knowledge_lost: number;
  knowledge_remaining: number;
  effective_owners_after: number;
  critical: boolean;
  recovery_estimate_weeks: number;
  succession: { pair_with: string; current_weight: number }[];
}

export interface BusFactorSim {
  person: string;
  person_id: string;
  services_impacted: number;
  critical: BusFactorImpact[];
  details: BusFactorImpact[];
}

export interface OrgBusFactorRow {
  person: string;
  person_id: string;
  critical_services: number;
  services_impacted: number;
}

export interface AskAnswer {
  answer: string;
  evidence: string[];
  hint?: string;
  detail?: unknown;
}

export interface QualityReport {
  services: number;
  by_repo: Record<string, string[]>;
  content_only_services: number;
  co_change_edges: number;
  people: { humans: number; bots_filtered: number };
  commits: number;
  renames_tracked: number;
  dependency_edges: number;
  explained_edges: number;
  risks_derived: number;
  coverage: {
    services_with_born: number;
    services_with_eras: number;
    services_with_owners: number;
  };
  inspect: string[];
}

export interface SearchHit {
  id: string;
  kind: string;
  name: string;
}

export interface GenomeEvent {
  event_id: string;
  kind: string;
  occurred_at: number;
  ingested_at: number;
  actors: string[];
  subjects: string[];
  payload: { hash?: string; msg?: string; churn?: Record<string, number> };
}

export interface Person {
  id: string;
  name: string;
}

/** Insight Engine (dna/insights.py). */
export interface Recommendation {
  action: string;
  why: string;
  impact: number;      // 1-5
  risk: number;        // 1-5 (risk of taking the action)
  confidence: number;  // 0-1
  effort: "S" | "M" | "L";
  score: number;
}

export interface HiddenDependency {
  a: string;
  b: string;
  co_changes: number;
  since: string | null;
  note: string;
}

export interface InsightsDoc {
  generated_in_ms: number;
  overview: {
    services: number;
    age_days: number;
    commits_90d: number;
    languages: Record<string, number>;
    complexity_score: number;
    maintainability_score: number;
    maturity_score: number;
    score_formulas: Record<string, string>;
  };
  engineering_health: {
    ownership_concentration_gini: number;
    knowledge_distribution: Record<string, number>;
    churn_hotspots: { service: string; commits_90d: number }[];
    stable_modules: { service: string; dormant_days?: number }[];
    volatile_modules: { service: string; commits_90d: number; note: string }[];
  };
  architecture: {
    circular_dependencies: string[][];
    hidden_dependencies: HiddenDependency[];
    coupling: { pair: string; co_changes: number; declared: boolean }[];
    architectural_drift: { edge: string; since: string | null }[];
    evolution_timeline: { service: string; born: string | null; eras: number; origin: string | null }[];
    boundary_assessment: string;
  };
  risk_intelligence: {
    single_points_of_failure: OrgBusFactorRow[];
    unowned_services: string[];
    scaling_bottlenecks: { service: string; dependents: number; commits_90d: number; note: string }[];
    frequently_changing: { service: string; commits_90d: number }[];
  };
  knowledge_intelligence: {
    knowledge_silos: { service: string; holder: string; share: number; dependents: number }[];
    missing_documentation: string[];
    critical_contributors: OrgBusFactorRow[];
    historical_context: { service: string; born: string | null; origin: string | null }[];
    decision_mining: { decisions_mined: number; avg_confidence: number | null; note: string | null };
  };
  recommendations: Recommendation[];
  executive: {
    cto: string;
    engineering_manager: string;
    staff_engineer: string;
    platform_team: string;
  };
}
