const DEFAULT_LABELS: Record<string, string> = {
  hr: "HR Interview",
  technical: "Technical Interview",
  behavioral: "Behavioral Interview",
  coding: "Coding Interview",
  system_design: "System Design Interview",
  mock_company: "Mock Company Interview",
};

const DEFAULT_DURATION: Record<string, number> = {
  hr: 20,
  technical: 35,
  behavioral: 25,
  coding: 45,
  system_design: 45,
  mock_company: 40,
};

const DEFAULT_QUESTION_TARGET: Record<string, number> = {
  hr: 5,
  technical: 5,
  behavioral: 4,
  coding: 3,
  system_design: 4,
  mock_company: 6,
};

type BriefInput = {
  mode: string;
  label: string;
  company: string;
  difficulty: string;
  durationMinutes: number;
  focus: string;
  questionTarget: number;
  resumeText?: string;
  notes?: string;
};

export type InterviewBrief = {
  mode: string;
  label: string;
  company: string;
  difficulty: string;
  durationMinutes: number;
  focus: string;
  questionTarget: number;
  notes: string;
};

function normalizeMode(value?: string | null) {
  return (value || "").trim().toLowerCase().replace(/\s+/g, "_").replace(/-/g, "_");
}

function readValue(lines: string[], label: string) {
  const prefix = `${label.toLowerCase()}:`;
  const line = lines.find((entry) => entry.trim().toLowerCase().startsWith(prefix));
  if (!line) return "";
  return line.slice(line.indexOf(":") + 1).trim();
}

export function parseInterviewBrief(jobDescription?: string | null, fallbackType?: string, fallbackTitle?: string): InterviewBrief {
  const lines = (jobDescription || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const mode = normalizeMode(readValue(lines, "Simulation Mode") || fallbackType);
  const label = readValue(lines, "Interview Style") || DEFAULT_LABELS[mode] || fallbackTitle || "Interview";
  const company = readValue(lines, "Company") || "General Placement";
  const difficulty = readValue(lines, "Difficulty") || "Medium";
  const durationMinutes = Number(readValue(lines, "Duration")) || DEFAULT_DURATION[mode] || 35;
  const questionTarget = Number(readValue(lines, "Question Target")) || DEFAULT_QUESTION_TARGET[mode] || 5;
  const focus = readValue(lines, "Focus") || "General interview practice";
  const notes = readValue(lines, "Additional Notes") || "";

  return {
    mode,
    label: DEFAULT_LABELS[mode] || label,
    company,
    difficulty,
    durationMinutes,
    questionTarget,
    focus,
    notes,
  };
}

export function buildInterviewBrief(input: BriefInput) {
  const lines = [
    `Simulation Mode: ${input.mode}`,
    `Interview Style: ${input.label}`,
    `Company: ${input.company}`,
    `Difficulty: ${input.difficulty}`,
    `Duration: ${input.durationMinutes}`,
    `Question Target: ${input.questionTarget}`,
    `Focus: ${input.focus}`,
    input.notes ? `Additional Notes: ${input.notes}` : "",
    input.resumeText ? `Resume Context:\n${input.resumeText}` : "",
  ];

  return lines.filter(Boolean).join("\n");
}

export function getInterviewDisplayTitle(jobDescription?: string | null, fallbackType?: string, fallbackTitle?: string) {
  return parseInterviewBrief(jobDescription, fallbackType, fallbackTitle).label;
}

export function getInterviewQuestionTarget(jobDescription?: string | null, fallbackType?: string) {
  return parseInterviewBrief(jobDescription, fallbackType).questionTarget;
}

export function getInterviewDuration(jobDescription?: string | null, fallbackType?: string) {
  return parseInterviewBrief(jobDescription, fallbackType).durationMinutes;
}
