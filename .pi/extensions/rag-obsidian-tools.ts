import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { promises as fs } from "node:fs";
import { extname, join, relative, resolve } from "node:path";

function stripAt(path: string): string {
  return path.startsWith("@") ? path.slice(1) : path;
}

function ensureInside(base: string, target: string): string {
  const absBase = resolve(base);
  const absTarget = resolve(target);
  const rel = relative(absBase, absTarget);
  if (rel.startsWith("..") || rel.includes("../") || rel.includes("..\\")) {
    throw new Error("Caminho fora do diretorio permitido");
  }
  return absTarget;
}

async function walkMarkdown(root: string): Promise<string[]> {
  const out: string[] = [];
  const stack = [root];

  while (stack.length) {
    const dir = stack.pop()!;
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        if ([".git", ".obsidian", "node_modules", ".venv", "downloads", "sources"].includes(entry.name)) continue;
        stack.push(full);
      } else if (entry.isFile() && extname(entry.name).toLowerCase() === ".md") {
        out.push(full);
      }
    }
  }

  return out;
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "ask_rag",
    label: "Ask RAG",
    description: "Faz retrieval local no projeto-rag e devolve contexto/citacoes",
    parameters: Type.Object({
      question: Type.String(),
      collection: Type.Optional(Type.String({ description: "Colecao sandeco_*_v1, auto ou all" })),
      top_k: Type.Optional(Type.Number({ minimum: 1, maximum: 20 })),
    }),
    async execute(_toolCallId, params) {
      const root = process.env.PROJETO_RAG_ROOT ?? "/home/ecode/Documents/projetos/projeto-rag";
      const python = process.env.RAG_PYTHON ?? `${root}/sources/rag_memory/02 - RAG with memory/.venv/bin/python`;
      const script = `${root}/scripts/rag_retrieve_local.py`;

      const args = [
        script,
        "--question",
        params.question,
        "--collection",
        params.collection ?? "auto",
        "--topk",
        String(params.top_k ?? 8),
      ];

      const result = await pi.exec(python, args, { timeout: 120000 });
      if (result.code !== 0) {
        return {
          content: [{ type: "text", text: `Falha no retrieval local: ${result.stderr || result.stdout}` }],
          details: { code: result.code },
          isError: true,
        };
      }

      let data: {
        collection: string;
        searched_collections?: string[];
        topk: number;
        chunks: Array<{ collection?: string; id?: string | null; distance?: number | null; metadata?: unknown; text: string }>;
      };

      try {
        const lines = result.stdout.trim().split(/\r?\n/).filter(Boolean);
        const jsonLine = lines[lines.length - 1] ?? "";
        data = JSON.parse(jsonLine);
      } catch {
        return {
          content: [{ type: "text", text: `Saida invalida do script de retrieval: ${result.stdout.slice(0, 800)}` }],
          details: {},
          isError: true,
        };
      }

      const preview = (data.chunks || []).map((c, i) => {
        const score = c.distance != null ? `distance=${c.distance.toFixed(4)}` : "distance=n/a";
        const from = c.collection ? ` | ${c.collection}` : "";
        return `### Chunk ${i + 1} (${score}${from})\n${(c.text || "").slice(0, 1200)}`;
      });

      return {
        content: [{
          type: "text",
          text: preview.length
            ? `Colecao: ${data.collection}\nBuscou em: ${(data.searched_collections || [data.collection]).join(", ")}\n\n${preview.join("\n\n")}`
            : `Colecao: ${data.collection}\nNenhum chunk retornado.`,
        }],
        details: {
          collection: data.collection,
          searched_collections: data.searched_collections || [data.collection],
          topk: data.topk,
          citations: data.chunks || [],
        },
      };
    },
  });

  pi.registerTool({
    name: "list_rag_collections",
    label: "List RAG Collections",
    description: "Lista as colecoes disponiveis no Chroma do projeto-rag",
    parameters: Type.Object({}),
    async execute() {
      const root = process.env.PROJETO_RAG_ROOT ?? "/home/ecode/Documents/projetos/projeto-rag";
      const python = process.env.RAG_PYTHON ?? `${root}/sources/rag_memory/02 - RAG with memory/.venv/bin/python`;
      const script = `${root}/scripts/rag_retrieve_local.py`;

      const result = await pi.exec(python, [script, "--list-collections"], { timeout: 120000 });
      if (result.code !== 0) {
        return {
          content: [{ type: "text", text: `Falha ao listar colecoes: ${result.stderr || result.stdout}` }],
          details: { code: result.code },
          isError: true,
        };
      }

      try {
        const lines = result.stdout.trim().split(/\r?\n/).filter(Boolean);
        const jsonLine = lines[lines.length - 1] ?? "";
        const data = JSON.parse(jsonLine) as { collections?: string[] };
        const cols = data.collections || [];
        return {
          content: [{ type: "text", text: cols.length ? cols.map((c) => `- ${c}`).join("\n") : "Nenhuma colecao." }],
          details: { collections: cols },
        };
      } catch {
        return {
          content: [{ type: "text", text: `Saida invalida: ${result.stdout.slice(0, 800)}` }],
          details: {},
          isError: true,
        };
      }
    },
  });

  pi.registerTool({
    name: "obsidian_search_notes",
    label: "Search Obsidian Notes",
    description: "Busca texto no vault Obsidian",
    parameters: Type.Object({
      query: Type.String(),
      max_results: Type.Optional(Type.Number({ minimum: 1, maximum: 20 })),
      path_prefix: Type.Optional(Type.String()),
    }),
    async execute(_toolCallId, params) {
      const vaultRoot = process.env.OBSIDIAN_VAULT_PATH ?? "/home/ecode/Documents/projetos/obsidian/obsidian-vault";
      const files = await walkMarkdown(vaultRoot);
      const q = params.query.toLowerCase().trim();
      const max = params.max_results ?? 8;
      const prefix = params.path_prefix?.trim();

      const hits: Array<{ path: string; line: number; snippet: string }> = [];

      for (const abs of files) {
        const rel = relative(vaultRoot, abs);
        if (prefix && !rel.startsWith(prefix)) continue;

        const content = await fs.readFile(abs, "utf8");
        const lines = content.split(/\r?\n/);
        for (let i = 0; i < lines.length; i++) {
          if (lines[i].toLowerCase().includes(q)) {
            hits.push({ path: rel, line: i + 1, snippet: lines[i].trim() });
            if (hits.length >= max) break;
          }
        }
        if (hits.length >= max) break;
      }

      return {
        content: [{
          type: "text",
          text: hits.length
            ? hits.map((h) => `- ${h.path}:${h.line} | ${h.snippet}`).join("\n")
            : "Nenhum resultado.",
        }],
        details: { vaultRoot, results: hits },
      };
    },
  });

  pi.registerTool({
    name: "obsidian_read_note",
    label: "Read Obsidian Note",
    description: "Le uma nota do Obsidian por caminho relativo ao vault",
    parameters: Type.Object({
      path: Type.String(),
    }),
    async execute(_toolCallId, params) {
      const vaultRoot = process.env.OBSIDIAN_VAULT_PATH ?? "/home/ecode/Documents/projetos/obsidian/obsidian-vault";
      const clean = stripAt(params.path);
      const abs = ensureInside(vaultRoot, resolve(vaultRoot, clean));
      const content = await fs.readFile(abs, "utf8");
      const limit = 18000;

      return {
        content: [{ type: "text", text: content.slice(0, limit) }],
        details: {
          vaultRoot,
          path: relative(vaultRoot, abs),
          truncated: content.length > limit,
        },
      };
    },
  });
}
