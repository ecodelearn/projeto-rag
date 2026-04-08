import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { promises as fs } from "node:fs";
import { relative, resolve } from "node:path";
import { stripAt, ensureInside, parseRagOutput, walkMarkdown, ParseError } from "./rag-obsidian-tools.utils.ts";

function parseLastJson<T = unknown>(raw: string): T {
  const txt = (raw || "").trim();
  if (!txt) throw new Error("Saida vazia do script");

  try {
    return JSON.parse(txt) as T;
  } catch {
    const start = txt.lastIndexOf("{");
    if (start >= 0) {
      const candidate = txt.slice(start);
      return JSON.parse(candidate) as T;
    }
    throw new Error(`Saida invalida: ${txt.slice(0, 800)}`);
  }
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

      let data: ReturnType<typeof parseRagOutput>;
      try {
        data = parseRagOutput(result.stdout);
      } catch (e) {
        return {
          content: [{ type: "text", text: e instanceof ParseError ? e.message : `Saida invalida do script de retrieval: ${result.stdout.slice(0, 800)}` }],
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
        const data = parseLastJson<{ collections?: string[] }>(result.stdout);
        const cols = data.collections || [];
        return {
          content: [{ type: "text", text: cols.length ? cols.map((c) => `- ${c}`).join("\n") : "Nenhuma colecao." }],
          details: { collections: cols },
        };
      } catch (e) {
        return {
          content: [{ type: "text", text: e instanceof Error ? e.message : `Saida invalida: ${result.stdout.slice(0, 800)}` }],
          details: {},
          isError: true,
        };
      }
    },
  });

  pi.registerTool({
    name: "ingest_rag_source",
    label: "Ingest RAG Source",
    description: "Ingere fonte web ou arquivos no pipeline dual sink (Obsidian bruto + Chroma)",
    parameters: Type.Object({
      source_type: Type.Union([Type.Literal("web"), Type.Literal("file")]),
      source_name: Type.String({ description: "slug logico da fonte (ex.: fastapi_docs)" }),
      collection: Type.String({ description: "colecao destino (ex.: docs_fastapi_v1)" }),
      url: Type.Optional(Type.String()),
      input_path: Type.Optional(Type.String()),
      allow_domain: Type.Optional(Type.String()),
      max_pages: Type.Optional(Type.Number({ minimum: 1, maximum: 500 })),
      max_depth: Type.Optional(Type.Number({ minimum: 0, maximum: 8 })),
      chunk_size: Type.Optional(Type.Number({ minimum: 300, maximum: 5000 })),
      overlap: Type.Optional(Type.Number({ minimum: 0, maximum: 1200 })),
      embedding_model: Type.Optional(Type.String()),
    }),
    async execute(_toolCallId, params) {
      const root = process.env.PROJETO_RAG_ROOT ?? "/home/ecode/Documents/projetos/projeto-rag";
      const python = process.env.RAG_PYTHON ?? `${root}/sources/rag_memory/02 - RAG with memory/.venv/bin/python`;
      const script = `${root}/scripts/ingest_dual_sink.py`;

      const args = [
        script,
        "--source-type", params.source_type,
        "--source-name", params.source_name,
        "--collection", params.collection,
      ];

      if (params.source_type === "web") {
        if (!params.url) {
          return {
            content: [{ type: "text", text: "Para source_type=web, passe o parametro url." }],
            details: {},
            isError: true,
          };
        }
        args.push("--url", params.url);
        if (params.allow_domain) args.push("--allow-domain", params.allow_domain);
        args.push("--max-pages", String(params.max_pages ?? 80));
        args.push("--max-depth", String(params.max_depth ?? 2));
      } else {
        if (!params.input_path) {
          return {
            content: [{ type: "text", text: "Para source_type=file, passe o parametro input_path." }],
            details: {},
            isError: true,
          };
        }
        args.push("--input-path", params.input_path);
      }

      if (params.chunk_size != null) args.push("--chunk-size", String(params.chunk_size));
      if (params.overlap != null) args.push("--overlap", String(params.overlap));
      if (params.embedding_model) args.push("--embedding-model", params.embedding_model);

      const result = await pi.exec(python, args, { timeout: 600000 });
      if (result.code !== 0) {
        return {
          content: [{ type: "text", text: `Falha na ingestao dual sink: ${result.stderr || result.stdout}` }],
          details: { code: result.code },
          isError: true,
        };
      }

      try {
        const data = parseLastJson<{
          source_type: string;
          source_name: string;
          collection: string;
          vault_manifest: string;
          items_collected: number;
          stats: { processed: number; upserted_chunks: number; skipped_unchanged: number; errors: number };
          state_file: string;
          timestamp: string;
        }>(result.stdout);

        return {
          content: [{
            type: "text",
            text: [
              `✅ Ingestao concluida`,
              `- source_type: ${data.source_type}`,
              `- source_name: ${data.source_name}`,
              `- collection: ${data.collection}`,
              `- items_collected: ${data.items_collected}`,
              `- processed: ${data.stats?.processed ?? 0}`,
              `- upserted_chunks: ${data.stats?.upserted_chunks ?? 0}`,
              `- skipped_unchanged: ${data.stats?.skipped_unchanged ?? 0}`,
              `- errors: ${data.stats?.errors ?? 0}`,
              `- manifest: ${data.vault_manifest}`,
              `- state: ${data.state_file}`,
            ].join("\n"),
          }],
          details: data,
        };
      } catch (e) {
        return {
          content: [{ type: "text", text: e instanceof Error ? e.message : `Saida invalida da ingestao: ${result.stdout.slice(0, 1000)}` }],
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
