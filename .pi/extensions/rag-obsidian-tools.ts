import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { promises as fs } from "node:fs";
import { join, relative, resolve } from "node:path";
import { stripAt, ensureInside, parseRagOutput, walkMarkdown, ParseError } from "./rag-obsidian-tools.utils.ts";

function parseLastJson<T = unknown>(raw: string): T {
  const txt = (raw || "").trim();
  if (!txt) throw new Error("Saida vazia do script");

  try {
    return JSON.parse(txt) as T;
  } catch {
    const lines = txt.split(/\r?\n/).filter(Boolean);
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();
      if (!line.startsWith("{")) continue;
      try {
        return JSON.parse(line) as T;
      } catch {
        continue;
      }
    }
    throw new Error(`Saida invalida: ${txt.slice(0, 800)}`);
  }
}

type TelemetryEvent = {
  ts: string;
  tool: string;
  category: string;
  outcome: "ok" | "error";
  duration_ms?: number;
  project?: string;
  action?: string;
  repetitive?: boolean;
  automation_candidate?: boolean;
  blocked_reason?: string;
  note?: string;
  params?: unknown;
  details?: unknown;
};

function truncateText(v: string | undefined, max = 600): string | undefined {
  if (!v) return v;
  return v.length > max ? `${v.slice(0, max)}...` : v;
}

function telemetryPaths(vaultRoot: string) {
  const base = join(vaultRoot, "90 Operacao", "Telemetria");
  const day = new Date().toISOString().slice(0, 10);
  return {
    eventsPath: join(base, "events.jsonl"),
    dailyPath: join(base, "Diario", `${day}.md`),
    reportsDir: join(base, "Relatorios"),
  };
}

function toDailyLine(ev: TelemetryEvent): string {
  const t = new Date(ev.ts).toTimeString().slice(0, 8);
  const msg = [
    `${t}`,
    `tool=${ev.tool}`,
    `outcome=${ev.outcome}`,
    ev.duration_ms != null ? `duration_ms=${ev.duration_ms}` : undefined,
    ev.project ? `project=${ev.project}` : undefined,
    ev.action ? `action=${ev.action}` : undefined,
    ev.blocked_reason ? `blocked=${ev.blocked_reason}` : undefined,
  ].filter(Boolean).join(" | ");

  return `- ${msg}`;
}

async function appendTelemetryEvent(vaultRoot: string, event: Omit<TelemetryEvent, "ts">) {
  const ev: TelemetryEvent = {
    ts: new Date().toISOString(),
    ...event,
    note: truncateText(event.note),
  };

  const { eventsPath, dailyPath } = telemetryPaths(vaultRoot);
  await fs.mkdir(resolve(eventsPath, ".."), { recursive: true });
  await fs.mkdir(resolve(dailyPath, ".."), { recursive: true });

  await fs.appendFile(eventsPath, JSON.stringify(ev, null, 0) + "\n", "utf8");

  try {
    await fs.access(dailyPath);
  } catch {
    await fs.writeFile(dailyPath, `# Diario de Telemetria - ${new Date().toISOString().slice(0, 10)}\n\n`, "utf8");
  }
  await fs.appendFile(dailyPath, toDailyLine(ev) + "\n", "utf8");
}

async function loadTelemetryEvents(vaultRoot: string): Promise<TelemetryEvent[]> {
  const { eventsPath } = telemetryPaths(vaultRoot);
  try {
    const raw = await fs.readFile(eventsPath, "utf8");
    return raw
      .split(/\r?\n/)
      .map((ln) => ln.trim())
      .filter(Boolean)
      .map((ln) => {
        try {
          return JSON.parse(ln) as TelemetryEvent;
        } catch {
          return null;
        }
      })
      .filter((x): x is TelemetryEvent => x !== null);
  } catch {
    return [];
  }
}

function summarizeTelemetry(events: TelemetryEvent[], days: number, topN: number) {
  const now = Date.now();
  const cutoff = now - days * 24 * 60 * 60 * 1000;
  const filtered = events.filter((e) => {
    const t = Date.parse(e.ts || "");
    return Number.isFinite(t) && t >= cutoff;
  });

  const byTool = new Map<string, { count: number; errors: number; totalMs: number }>();
  const blockers = new Map<string, number>();
  let repetitive = 0;
  let automation = 0;

  for (const e of filtered) {
    const k = e.tool || "unknown";
    const row = byTool.get(k) || { count: 0, errors: 0, totalMs: 0 };
    row.count += 1;
    if (e.outcome === "error") row.errors += 1;
    if (typeof e.duration_ms === "number") row.totalMs += e.duration_ms;
    byTool.set(k, row);

    if (e.blocked_reason) blockers.set(e.blocked_reason, (blockers.get(e.blocked_reason) || 0) + 1);
    if (e.repetitive) repetitive += 1;
    if (e.automation_candidate) automation += 1;
  }

  const topTools = [...byTool.entries()]
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, topN)
    .map(([tool, v]) => ({
      tool,
      count: v.count,
      errors: v.errors,
      avg_ms: v.count ? Math.round(v.totalMs / v.count) : 0,
    }));

  const topBlockers = [...blockers.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([reason, count]) => ({ reason, count }));

  const total = filtered.length;
  const errorRate = total ? Number(((filtered.filter((e) => e.outcome === "error").length / total) * 100).toFixed(2)) : 0;

  return {
    total,
    days,
    error_rate_pct: errorRate,
    repetitive_count: repetitive,
    automation_candidates: automation,
    top_tools: topTools,
    top_blockers: topBlockers,
  };
}

function markdownReport(summary: ReturnType<typeof summarizeTelemetry>, eventsPath: string) {
  const lines: string[] = [];
  lines.push(`# Relatorio de Telemetria (${summary.days} dias)`);
  lines.push("");
  lines.push(`- Total de eventos: **${summary.total}**`);
  lines.push(`- Taxa de erro: **${summary.error_rate_pct}%**`);
  lines.push(`- Eventos repetitivos: **${summary.repetitive_count}**`);
  lines.push(`- Candidatos a automacao: **${summary.automation_candidates}**`);
  lines.push(`- Fonte: \
\`${eventsPath}\``);
  lines.push("");

  lines.push("## Top tools");
  if (!summary.top_tools.length) {
    lines.push("- Sem dados no periodo.");
  } else {
    for (const t of summary.top_tools) {
      lines.push(`- \`${t.tool}\`: ${t.count} uso(s), erros=${t.errors}, media=${t.avg_ms}ms`);
    }
  }

  lines.push("");
  lines.push("## Top bloqueios");
  if (!summary.top_blockers.length) {
    lines.push("- Sem bloqueios registrados.");
  } else {
    for (const b of summary.top_blockers) {
      lines.push(`- ${b.reason}: ${b.count}`);
    }
  }

  lines.push("");
  lines.push("## Sinais de automacao");
  lines.push("- Priorizar automacao onde houver alta repeticao + bloqueio recorrente.");
  lines.push("- Avaliar criar/ajustar subagents para os 2 tools mais frequentes.");

  return lines.join("\n");
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
      const started = Date.now();
      const root = process.env.PROJETO_RAG_ROOT ?? "/home/ecode/Documents/projetos/projeto-rag";
      const vaultRoot = process.env.OBSIDIAN_VAULT_PATH ?? "/home/ecode/Documents/projetos/obsidian/obsidian-vault";
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
        await appendTelemetryEvent(vaultRoot, {
          tool: "ask_rag",
          category: "rag",
          outcome: "error",
          duration_ms: Date.now() - started,
          blocked_reason: "retrieval_exec_failed",
          note: truncateText(result.stderr || result.stdout),
          params: { collection: params.collection ?? "auto", top_k: params.top_k ?? 8 },
        });
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
        await appendTelemetryEvent(vaultRoot, {
          tool: "ask_rag",
          category: "rag",
          outcome: "error",
          duration_ms: Date.now() - started,
          blocked_reason: "retrieval_parse_failed",
          note: e instanceof Error ? e.message : "parse_error",
          params: { collection: params.collection ?? "auto", top_k: params.top_k ?? 8 },
        });
        return {
          content: [{ type: "text", text: e instanceof ParseError ? e.message : `Saida invalida do script de retrieval: ${result.stdout.slice(0, 800)}` }],
          details: {},
          isError: true,
        };
      }

      await appendTelemetryEvent(vaultRoot, {
        tool: "ask_rag",
        category: "rag",
        outcome: "ok",
        duration_ms: Date.now() - started,
        action: "retrieval",
        params: { collection: params.collection ?? "auto", top_k: params.top_k ?? 8 },
        details: { result_collection: data.collection, chunks: (data.chunks || []).length },
      });

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
      const started = Date.now();
      const root = process.env.PROJETO_RAG_ROOT ?? "/home/ecode/Documents/projetos/projeto-rag";
      const vaultRoot = process.env.OBSIDIAN_VAULT_PATH ?? "/home/ecode/Documents/projetos/obsidian/obsidian-vault";
      const python = process.env.RAG_PYTHON ?? `${root}/sources/rag_memory/02 - RAG with memory/.venv/bin/python`;
      const script = `${root}/scripts/rag_retrieve_local.py`;

      const result = await pi.exec(python, [script, "--list-collections"], { timeout: 120000 });
      if (result.code !== 0) {
        await appendTelemetryEvent(vaultRoot, {
          tool: "list_rag_collections",
          category: "rag",
          outcome: "error",
          duration_ms: Date.now() - started,
          blocked_reason: "list_exec_failed",
          note: truncateText(result.stderr || result.stdout),
        });
        return {
          content: [{ type: "text", text: `Falha ao listar colecoes: ${result.stderr || result.stdout}` }],
          details: { code: result.code },
          isError: true,
        };
      }

      try {
        const data = parseLastJson<{ collections?: string[] }>(result.stdout);
        const cols = data.collections || [];
        await appendTelemetryEvent(vaultRoot, {
          tool: "list_rag_collections",
          category: "rag",
          outcome: "ok",
          duration_ms: Date.now() - started,
          action: "list_collections",
          details: { count: cols.length },
        });
        return {
          content: [{ type: "text", text: cols.length ? cols.map((c) => `- ${c}`).join("\n") : "Nenhuma colecao." }],
          details: { collections: cols },
        };
      } catch (e) {
        await appendTelemetryEvent(vaultRoot, {
          tool: "list_rag_collections",
          category: "rag",
          outcome: "error",
          duration_ms: Date.now() - started,
          blocked_reason: "list_parse_failed",
          note: e instanceof Error ? e.message : "parse_error",
        });
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
      const started = Date.now();
      const root = process.env.PROJETO_RAG_ROOT ?? "/home/ecode/Documents/projetos/projeto-rag";
      const vaultRoot = process.env.OBSIDIAN_VAULT_PATH ?? "/home/ecode/Documents/projetos/obsidian/obsidian-vault";
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
          await appendTelemetryEvent(vaultRoot, {
            tool: "ingest_rag_source",
            category: "ingest",
            outcome: "error",
            duration_ms: Date.now() - started,
            blocked_reason: "missing_url",
            params,
          });
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
          await appendTelemetryEvent(vaultRoot, {
            tool: "ingest_rag_source",
            category: "ingest",
            outcome: "error",
            duration_ms: Date.now() - started,
            blocked_reason: "missing_input_path",
            params,
          });
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
        await appendTelemetryEvent(vaultRoot, {
          tool: "ingest_rag_source",
          category: "ingest",
          outcome: "error",
          duration_ms: Date.now() - started,
          blocked_reason: "ingest_exec_failed",
          note: truncateText(result.stderr || result.stdout),
          params,
        });
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

        await appendTelemetryEvent(vaultRoot, {
          tool: "ingest_rag_source",
          category: "ingest",
          outcome: "ok",
          duration_ms: Date.now() - started,
          action: data.source_type,
          params: {
            source_type: params.source_type,
            source_name: params.source_name,
            collection: params.collection,
          },
          details: {
            items_collected: data.items_collected,
            upserted_chunks: data.stats?.upserted_chunks ?? 0,
            errors: data.stats?.errors ?? 0,
          },
        });

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
        await appendTelemetryEvent(vaultRoot, {
          tool: "ingest_rag_source",
          category: "ingest",
          outcome: "error",
          duration_ms: Date.now() - started,
          blocked_reason: "ingest_parse_failed",
          note: e instanceof Error ? e.message : "parse_error",
          params,
        });
        return {
          content: [{ type: "text", text: e instanceof Error ? e.message : `Saida invalida da ingestao: ${result.stdout.slice(0, 1000)}` }],
          details: {},
          isError: true,
        };
      }
    },
  });

  pi.registerTool({
    name: "track_work_event",
    label: "Track Work Event",
    description: "Registra evento operacional no Obsidian (telemetria leve sem LLM)",
    parameters: Type.Object({
      category: Type.String({ description: "ex.: rag, ingest, refactor, debug, docs" }),
      action: Type.String({ description: "acao curta" }),
      project: Type.Optional(Type.String()),
      outcome: Type.Optional(Type.Union([Type.Literal("ok"), Type.Literal("error")])),
      duration_ms: Type.Optional(Type.Number({ minimum: 0 })),
      repetitive: Type.Optional(Type.Boolean()),
      automation_candidate: Type.Optional(Type.Boolean()),
      blocked_reason: Type.Optional(Type.String()),
      note: Type.Optional(Type.String()),
    }),
    async execute(_toolCallId, params) {
      const vaultRoot = process.env.OBSIDIAN_VAULT_PATH ?? "/home/ecode/Documents/projetos/obsidian/obsidian-vault";
      await appendTelemetryEvent(vaultRoot, {
        tool: "track_work_event",
        category: params.category,
        action: params.action,
        project: params.project,
        outcome: params.outcome ?? "ok",
        duration_ms: params.duration_ms,
        repetitive: params.repetitive,
        automation_candidate: params.automation_candidate,
        blocked_reason: params.blocked_reason,
        note: params.note,
      });

      const { eventsPath, dailyPath } = telemetryPaths(vaultRoot);
      return {
        content: [{ type: "text", text: `✅ Evento registrado\n- events: ${eventsPath}\n- diario: ${dailyPath}` }],
        details: { events_path: eventsPath, daily_path: dailyPath },
      };
    },
  });

  pi.registerTool({
    name: "analyze_work_patterns",
    label: "Analyze Work Patterns",
    description: "Analisa eventos de telemetria e gera relatorio sem usar LLM",
    parameters: Type.Object({
      days: Type.Optional(Type.Number({ minimum: 1, maximum: 90 })),
      top_n: Type.Optional(Type.Number({ minimum: 1, maximum: 20 })),
      write_note: Type.Optional(Type.Boolean()),
    }),
    async execute(_toolCallId, params) {
      const vaultRoot = process.env.OBSIDIAN_VAULT_PATH ?? "/home/ecode/Documents/projetos/obsidian/obsidian-vault";
      const days = Math.max(1, Math.min(90, Math.floor(params.days ?? 7)));
      const topN = Math.max(1, Math.min(20, Math.floor(params.top_n ?? 8)));
      const writeNote = params.write_note ?? true;

      const events = await loadTelemetryEvents(vaultRoot);
      const summary = summarizeTelemetry(events, days, topN);
      const { eventsPath, reportsDir } = telemetryPaths(vaultRoot);
      const reportMd = markdownReport(summary, eventsPath);

      let notePath: string | null = null;
      if (writeNote) {
        await fs.mkdir(reportsDir, { recursive: true });
        const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
        notePath = join(reportsDir, `Relatorio-${stamp}.md`);
        await fs.writeFile(notePath, reportMd + "\n", "utf8");
      }

      await appendTelemetryEvent(vaultRoot, {
        tool: "analyze_work_patterns",
        category: "telemetry",
        outcome: "ok",
        action: "analyze",
        details: { days, top_n: topN, total: summary.total, note_path: notePath },
      });

      return {
        content: [{ type: "text", text: reportMd + (notePath ? `\n\nNota salva em: ${notePath}` : "") }],
        details: { summary, note_path: notePath, events_path: eventsPath },
      };
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
      const started = Date.now();
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

      await appendTelemetryEvent(vaultRoot, {
        tool: "obsidian_search_notes",
        category: "obsidian",
        outcome: "ok",
        duration_ms: Date.now() - started,
        action: "search",
        params: { max_results: max, path_prefix: prefix },
        details: { hits: hits.length },
      });

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
      const started = Date.now();
      const vaultRoot = process.env.OBSIDIAN_VAULT_PATH ?? "/home/ecode/Documents/projetos/obsidian/obsidian-vault";
      const clean = stripAt(params.path);
      const abs = ensureInside(vaultRoot, resolve(vaultRoot, clean));
      const content = await fs.readFile(abs, "utf8");
      const limit = 18000;

      await appendTelemetryEvent(vaultRoot, {
        tool: "obsidian_read_note",
        category: "obsidian",
        outcome: "ok",
        duration_ms: Date.now() - started,
        action: "read",
        params: { path: clean },
      });

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
