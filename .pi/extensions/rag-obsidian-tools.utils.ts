import { promises as fs } from "node:fs";
import { extname, join, relative, resolve } from "node:path";

export function stripAt(path: string): string {
  return path.startsWith("@") ? path.slice(1) : path;
}

export function ensureInside(base: string, target: string): string {
  const absBase = resolve(base);
  const absTarget = resolve(target);
  const rel = relative(absBase, absTarget);
  if (rel.startsWith("..") || rel.includes("../") || rel.includes("..\\")) {
    throw new Error("Caminho fora do diretorio permitido");
  }
  return absTarget;
}

export type RagChunk = {
  id?: string | null;
  distance?: number | null;
  metadata?: unknown;
  text: string;
  collection?: string;
};

export type RagData = {
  collection: string;
  topk: number;
  chunks: RagChunk[];
  searched_collections?: string[];
};

export class ParseError extends Error {}

export function parseRagOutput(stdout: string): RagData {
  const lines = stdout.trim().split(/\r?\n/).filter(Boolean);

  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i].trim();
    if (!line.startsWith("{")) continue;
    let parsed: unknown;
    try {
      parsed = JSON.parse(line);
    } catch {
      continue;
    }
    if (
      parsed !== null &&
      typeof parsed === "object" &&
      "collection" in parsed &&
      "topk" in parsed &&
      "chunks" in parsed
    ) {
      return parsed as RagData;
    }
  }

  throw new ParseError(`Saida invalida do script de retrieval: ${stdout.slice(0, 800)}`);
}

const IGNORED_DIRS = new Set([
  ".git",
  ".obsidian",
  "node_modules",
  ".venv",
  "downloads",
  "sources",
]);

export async function walkMarkdown(root: string): Promise<string[]> {
  const out: string[] = [];
  const stack = [root];

  while (stack.length) {
    const dir = stack.pop()!;
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        if (IGNORED_DIRS.has(entry.name)) continue;
        stack.push(full);
      } else if (entry.isFile() && extname(entry.name).toLowerCase() === ".md") {
        out.push(full);
      }
    }
  }

  return out;
}

export default function () {}
