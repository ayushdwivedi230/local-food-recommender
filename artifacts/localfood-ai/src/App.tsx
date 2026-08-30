import { type FormEvent, useMemo, useState } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  BadgeIndianRupee,
  Check,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  Compass,
  Database,
  Gauge,
  Leaf,
  MapPin,
  MessageCircle,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  Star,
  Trash2,
  Utensils,
  Zap,
} from 'lucide-react';
import type { AgentResponse, MemoryState, Recommendation, ActivityEvent, TraceStep } from '@workspace/api-client-react';
import {
  getGetAgentMemoryQueryKey,
  useClearAgentMemory,
  useGetAgentMemory,
  useHealthCheck,
  useRunAgent,
} from '@workspace/api-client-react';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Route, Switch, Router as WouterRouter } from 'wouter';

const queryClient = new QueryClient();

type ChatLine = { id: string; role: 'user' | 'assistant'; text: string };

const starterPrompts = [
  'Find a quick vegetarian dinner under ₹500',
  'I want something spicy and regional',
  'What is good near Koramangala tonight?',
];

const fallbackMemory: MemoryState = {
  diet: null,
  preferredCuisine: null,
  dislikedCuisine: null,
  spicePreference: null,
  budget: null,
  location: null,
  updatedAt: '',
};

function Home() {
  const [sessionId] = useState(() => {
    const existing = sessionStorage.getItem('localfood-session');
    if (existing) return existing;
    const next = `demo-${crypto.randomUUID()}`;
    sessionStorage.setItem('localfood-session', next);
    return next;
  });
  const [draft, setDraft] = useState('');
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [conversation, setConversation] = useState<ChatLine[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'Tell me what sounds good, where you are, or what you want to avoid. I'll search the local list and show you how I got there.',
    },
  ]);
  const [clearedNotice, setClearedNotice] = useState(false);
  const memoryQuery = useGetAgentMemory(sessionId, {
    query: { queryKey: getGetAgentMemoryQueryKey(sessionId) },
  });
  const healthQuery = useHealthCheck();
  const runAgent = useRunAgent();
  const clearMemory = useClearAgentMemory();
  const client = useQueryClient();

  const memory = response?.memory ?? memoryQuery.data ?? fallbackMemory;
  const activity = response?.activity ?? [];
  const trace = response?.trace ?? [];
  const recommendations = response?.recommendations ?? [];
  const stats = response?.stats;
  const isWorking = runAgent.isPending;

  const sendMessage = (message: string) => {
    const clean = message.trim();
    if (!clean || isWorking) return;
    setClearedNotice(false);
    setDraft('');
    setConversation((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: 'user', text: clean },
    ]);
    runAgent.mutate(
      { data: { sessionId, message: clean } },
      {
        onSuccess: (next) => {
          setResponse(next);
          client.setQueryData(getGetAgentMemoryQueryKey(sessionId), next.memory);
          setConversation((current) => [
            ...current,
            { id: `assistant-${Date.now()}`, role: 'assistant', text: next.reply },
          ]);
        },
      },
    );
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    sendMessage(draft);
  };

  const handleClearMemory = () => {
    clearMemory.mutate(
      { sessionId },
      {
        onSuccess: (cleared) => {
          client.setQueryData(getGetAgentMemoryQueryKey(sessionId), cleared);
          setResponse((current) => (current ? { ...current, memory: cleared } : current));
          setClearedNotice(true);
        },
      },
    );
  };

  return (
    <div className="lf-shell flex min-h-[100dvh] flex-col md:flex-row">
      <aside className="lf-sidebar flex w-full shrink-0 flex-col md:min-h-[100dvh] md:w-[238px]">
        <div className="flex items-center justify-between px-5 py-5 md:block md:px-6 md:py-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-[13px] bg-[hsl(var(--secondary))] text-[hsl(var(--secondary-foreground))] shadow-[0_8px_22px_hsl(42_89%_62%_/_0.16)]">
              <Utensils size={20} strokeWidth={2.2} />
            </div>
            <div>
              <div className="lf-display text-[19px] font-semibold leading-none tracking-[-0.04em]">LocalFood</div>
              <div className="lf-mono mt-1 text-[9px] uppercase tracking-[0.16em] text-[hsl(var(--sidebar-foreground)/.54)]">AI / field notes</div>
            </div>
          </div>
          <div className="hidden pt-12 md:block">
            <div className="lf-mono mb-3 px-2 text-[9px] uppercase tracking-[0.16em] text-[hsl(var(--sidebar-foreground)/.4)]">Workspace</div>
            <nav className="space-y-1">
              <div className="flex items-center gap-3 rounded-xl bg-[hsl(var(--sidebar-accent))] px-3 py-3 text-sm font-semibold text-[hsl(var(--sidebar-foreground))]">
                <MessageCircle size={16} className="text-[hsl(var(--secondary))]" />
                Discover
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[hsl(var(--secondary))] shadow-[0_0_0_4px_hsl(42_89%_62%_/_0.12)]" />
              </div>
              <div className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-[hsl(var(--sidebar-foreground)/.58)]">
                <Database size={16} /> Restaurant index
              </div>
              <div className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-[hsl(var(--sidebar-foreground)/.58)]">
                <Gauge size={16} /> Agent telemetry
              </div>
            </nav>
          </div>
        </div>
        <div className="hidden flex-1 md:block" />
        <div className="hidden border-t border-[hsl(var(--sidebar-border))] px-6 py-6 md:block">
          <div className="lf-mono mb-3 text-[9px] uppercase tracking-[0.16em] text-[hsl(var(--sidebar-foreground)/.4)]">Session</div>
          <div className="mb-3 flex items-center gap-2 text-xs text-[hsl(var(--sidebar-foreground)/.65)]">
            <span className={`h-2 w-2 rounded-full ${healthQuery.isError ? 'bg-[hsl(var(--accent))]' : 'lf-pulse bg-[hsl(147_48%_55%)]'}`} />
            {healthQuery.isError ? 'Agent offline' : healthQuery.data?.status ?? 'Checking agent'}
          </div>
          <div className="lf-mono truncate text-[10px] text-[hsl(var(--sidebar-foreground)/.35)]">{sessionId}</div>
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        <header className="flex items-center justify-between border-b border-[hsl(var(--border)/.75)] px-5 py-4 md:px-9 md:py-5">
          <div className="flex items-center gap-2 text-xs font-semibold text-[hsl(var(--muted-foreground))]">
            <Compass size={15} className="text-[hsl(var(--accent))]" />
            <span>Local discovery lab</span>
            <span className="hidden text-[hsl(var(--border))] sm:inline">/</span>
            <span className="hidden font-normal sm:inline">Punjab &amp; North India demo dataset</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--card)/.65)] px-3 py-1.5 text-[11px] font-semibold text-[hsl(var(--muted-foreground))] sm:flex">
              <span className={`h-1.5 w-1.5 rounded-full ${healthQuery.isError ? 'bg-[hsl(var(--accent))]' : 'bg-[hsl(147_48%_42%)]'}`} />
              {healthQuery.isError ? 'Needs attention' : 'Python agent ready'}
            </div>
          </div>
        </header>

        <div className="mx-auto grid max-w-[1500px] gap-6 px-5 py-7 md:px-9 md:py-9 xl:grid-cols-[minmax(0,1.04fr)_minmax(380px,.76fr)]">
          <section className="min-w-0">
            <div className="lf-enter mb-7">
              <div className="mb-3 flex items-center gap-2">
                <span className="lf-mono rounded-full bg-[hsl(var(--secondary)/.28)] px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.13em] text-[hsl(25_29%_30%)]">Conversational recommender</span>
                {response?.mode && <span className="lf-mono rounded-full border border-[hsl(var(--border))] px-2.5 py-1 text-[10px] uppercase tracking-[0.13em] text-[hsl(var(--muted-foreground))]">{response.mode} mode</span>}
              </div>
              <h1 className="lf-display max-w-[680px] text-[clamp(2.5rem,5vw,4.65rem)] font-semibold leading-[.98] text-[hsl(var(--foreground))]">
                Food that feels<br /><span className="text-[hsl(var(--accent))]">like your place.</span>
              </h1>
              <p className="mt-4 max-w-[570px] text-[15px] leading-7 text-[hsl(var(--muted-foreground))]">
                A little context goes a long way. Ask naturally and I'll turn your mood, map, and memory into a short list worth leaving the hostel for.
              </p>
            </div>

            <div className="lf-card lf-enter lf-enter-delay-1 rounded-[22px] p-3 sm:p-4">
              <form onSubmit={handleSubmit}>
                <label htmlFor="food-prompt" className="sr-only">Ask LocalFood AI</label>
                <textarea
                  id="food-prompt"
                  data-testid="input-food-prompt"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault();
                      sendMessage(draft);
                    }
                  }}
                  maxLength={1000}
                  rows={3}
                  placeholder="Try "I'm vegetarian and I like Punjabi food in Jalandhar…""
                  className="w-full resize-none border-0 bg-transparent px-2 py-1 text-[16px] leading-7 text-[hsl(var(--foreground))] outline-none placeholder:text-[hsl(var(--muted-foreground)/.64)]"
                />
                <div className="flex items-center justify-between border-t border-[hsl(var(--border)/.72)] pt-3">
                  <div className="flex items-center gap-2 px-2 text-[11px] text-[hsl(var(--muted-foreground))]">
                    <Sparkles size={14} className="text-[hsl(var(--secondary-foreground))]" />
                    <span className="hidden sm:inline">The more specific, the more local.</span>
                    <span className="sm:hidden">{draft.length}/1000</span>
                  </div>
                  <button
                    data-testid="button-send-prompt"
                    type="submit"
                    disabled={!draft.trim() || isWorking}
                    className="flex items-center gap-2 rounded-xl bg-[hsl(var(--primary))] px-4 py-2.5 text-xs font-bold text-[hsl(var(--primary-foreground))] transition hover:-translate-y-0.5 hover:bg-[hsl(25_29%_25%)] disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    {isWorking ? 'Searching' : 'Ask the agent'} <Send size={14} />
                  </button>
                </div>
              </form>
            </div>

            {!response && !isWorking && (
              <div className="lf-enter lf-enter-delay-2 mt-4">
                <div className="mb-2 px-1 text-[10px] font-bold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Good starting points</div>
                <div className="flex flex-wrap gap-2">
                  {starterPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      data-testid={`button-starter-${prompt.slice(0, 8).replace(/\s/g, '-').toLowerCase()}`}
                      onClick={() => sendMessage(prompt)}
                      className="rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--card)/.6)] px-3.5 py-2 text-xs font-medium text-[hsl(var(--foreground)/.78)] transition hover:-translate-y-0.5 hover:border-[hsl(var(--accent)/.55)] hover:bg-[hsl(var(--secondary)/.16)]"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="lf-enter lf-enter-delay-2 mt-8">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageCircle size={16} className="text-[hsl(var(--accent))]" />
                  <h2 className="text-sm font-bold">The conversation</h2>
                </div>
                <span className="lf-mono text-[10px] text-[hsl(var(--muted-foreground))]">{conversation.length} turns</span>
              </div>
              <div className="space-y-3">
                {conversation.map((line) => (
                  <div key={line.id} className={`flex ${line.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div data-testid={`message-${line.role}-${line.id}`} className={`max-w-[88%] rounded-2xl px-4 py-3 text-[14px] leading-6 ${line.role === 'user' ? 'rounded-br-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]' : 'rounded-bl-md border border-[hsl(var(--border))] bg-[hsl(var(--card)/.72)] text-[hsl(var(--foreground)/.84)]'}`}>
                      {line.role === 'assistant' && <div className="lf-mono mb-1.5 text-[9px] uppercase tracking-[0.15em] text-[hsl(var(--accent))]">LocalFood AI</div>}
                      <span style={{ whiteSpace: 'pre-line' }}>{line.text}</span>
                    </div>
                  </div>
                ))}
                {isWorking && (
                  <div data-testid="status-agent-loading" className="flex items-center gap-3 rounded-2xl rounded-bl-md border border-[hsl(var(--border))] bg-[hsl(var(--card)/.72)] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
                    <span className="flex gap-1"><i className="lf-pulse h-1.5 w-1.5 rounded-full bg-[hsl(var(--accent))]" /><i className="lf-pulse h-1.5 w-1.5 rounded-full bg-[hsl(var(--accent))]" style={{ animationDelay: '180ms' }} /><i className="lf-pulse h-1.5 w-1.5 rounded-full bg-[hsl(var(--accent))]" style={{ animationDelay: '360ms' }} /></span>
                    The agent is checking nearby tables…
                  </div>
                )}
                {runAgent.isError && (
                  <div data-testid="status-agent-error" className="flex items-start gap-3 rounded-2xl border border-[hsl(var(--accent)/.35)] bg-[hsl(var(--accent)/.08)] px-4 py-3 text-sm text-[hsl(var(--foreground))]">
                    <CircleAlert size={17} className="mt-0.5 shrink-0 text-[hsl(var(--accent))]" />
                    <div><strong>That search didn't land.</strong><div className="mt-0.5 text-[hsl(var(--muted-foreground))]">Check the agent connection and try again.</div></div>
                  </div>
                )}
              </div>
            </div>

            {response && (
              <div className="lf-enter mt-8">
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap size={16} className="text-[hsl(var(--secondary-foreground))]" />
                    <h2 className="text-sm font-bold">Fresh from the search</h2>
                  </div>
                  {stats && <span className="lf-mono text-[10px] text-[hsl(var(--muted-foreground))]">{stats.elapsedMs}ms / {stats.searched} indexed</span>}
                </div>
                {recommendations.length > 0 ? (
                  <div className="space-y-3">
                    {recommendations.map((restaurant, index) => <RecommendationCard key={restaurant.id} item={restaurant} index={index} />)}
                  </div>
                ) : (
                  <div data-testid="empty-recommendations" className="lf-card rounded-2xl px-5 py-7 text-center">
                    <Search size={20} className="mx-auto mb-2 text-[hsl(var(--muted-foreground))]" />
                    <p className="text-sm font-semibold">No close matches this turn.</p>
                    <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">Try widening the budget or changing the neighbourhood.</p>
                  </div>
                )}
              </div>
            )}
          </section>

          <aside className="min-w-0 space-y-5">
            <ActivityPanel activity={activity} working={isWorking} />
            <MemoryPanel memory={memory} loading={memoryQuery.isLoading} error={memoryQuery.isError} cleared={clearedNotice} onClear={handleClearMemory} clearing={clearMemory.isPending} />
            {response && <TracePanel trace={trace} stats={stats} />}
          </aside>
        </div>
      </main>
    </div>
  );
}

function ActivityPanel({ activity, working }: { activity: ActivityEvent[]; working: boolean }) {
  return (
    <section className="lf-card lf-enter lf-enter-delay-1 overflow-hidden rounded-[22px]">
      <div className="flex items-center justify-between border-b border-[hsl(var(--border)/.7)] px-5 py-4">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-[hsl(var(--accent))]" />
          <h2 className="text-sm font-bold">Agent activity</h2>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">
          <span className={`h-1.5 w-1.5 rounded-full ${working ? 'lf-pulse bg-[hsl(var(--accent))]' : 'bg-[hsl(147_48%_42%)]'}`} /> {working ? 'working' : 'standby'}
        </div>
      </div>
      <div className="p-5">
        {activity.length === 0 ? (
          <div data-testid="empty-activity" className="rounded-xl border border-dashed border-[hsl(var(--border))] px-4 py-6 text-center">
            <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-[hsl(var(--secondary)/.25)]"><Sparkles size={15} className="text-[hsl(var(--secondary-foreground))]" /></div>
            <p className="text-xs font-semibold">Your agent trail appears here.</p>
            <p className="mt-1 text-[11px] leading-5 text-[hsl(var(--muted-foreground))]">Ask for a craving, a place, or a constraint to start.</p>
          </div>
        ) : (
          <div className="relative space-y-4 before:absolute before:bottom-2 before:left-[8px] before:top-2 before:w-px before:bg-[hsl(var(--border))]">
            {activity.map((event) => <ActivityRow key={event.id} event={event} />)}
          </div>
        )}
      </div>
    </section>
  );
}

function ActivityRow({ event }: { event: ActivityEvent }) {
  const Icon = event.kind === 'tool' ? Search : event.kind === 'observation' ? Database : event.kind === 'decision' ? Check : event.kind === 'warning' ? CircleAlert : event.kind === 'success' ? CircleCheck : Sparkles;
  const color = event.kind === 'warning' ? 'text-[hsl(var(--accent))]' : event.kind === 'decision' || event.kind === 'success' ? 'text-[hsl(147_48%_40%)]' : 'text-[hsl(var(--secondary-foreground))]';
  return (
    <div data-testid={`activity-event-${event.id}`} className="relative flex gap-3">
      <div className={`relative z-[1] flex h-[17px] w-[17px] shrink-0 items-center justify-center rounded-full bg-[hsl(var(--card))] ${color}`}><Icon size={13} strokeWidth={2.4} /></div>
      <div className="min-w-0 -mt-0.5">
        <div className="flex items-center gap-2 text-xs font-bold">{event.label}{event.status === 'active' && <span className="lf-pulse h-1.5 w-1.5 rounded-full bg-[hsl(var(--accent))]" />}</div>
        <p className="mt-1 text-[11px] leading-5 text-[hsl(var(--muted-foreground))]">{event.detail}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Memory panel — shows only non-null values as coloured pills; a neutral
// placeholder when nothing has been stored yet.
// ---------------------------------------------------------------------------
function MemoryPanel({ memory, loading, error, cleared, onClear, clearing }: { memory: MemoryState; loading: boolean; error: boolean; cleared: boolean; onClear: () => void; clearing: boolean }) {
  const entries = useMemo<Array<{ label: string; value: string | null; color: string }>>(() => [
    { label: 'Diet', value: memory.diet, color: 'bg-[hsl(147_48%_38%/.15)] text-[hsl(147_48%_30%)] border-[hsl(147_48%_38%/.3)]' },
    { label: 'Cuisine', value: memory.preferredCuisine, color: 'bg-[hsl(42_89%_62%/.18)] text-[hsl(25_29%_28%)] border-[hsl(42_89%_62%/.4)]' },
    { label: 'Avoiding', value: memory.dislikedCuisine, color: 'bg-[hsl(var(--accent)/.12)] text-[hsl(15_72%_40%)] border-[hsl(var(--accent)/.3)]' },
    { label: 'Spice', value: memory.spicePreference, color: 'bg-[hsl(15_72%_61%/.12)] text-[hsl(15_60%_38%)] border-[hsl(15_72%_61%/.3)]' },
    { label: 'Budget', value: memory.budget ? `₹${memory.budget}/meal` : null, color: 'bg-[hsl(198_43%_47%/.12)] text-[hsl(198_43%_30%)] border-[hsl(198_43%_47%/.3)]' },
    { label: 'City', value: memory.location, color: 'bg-[hsl(277_24%_54%/.12)] text-[hsl(277_24%_35%)] border-[hsl(277_24%_54%/.3)]' },
  ], [memory]);

  const activeEntries = entries.filter((e) => e.value !== null);

  return (
    <section className="lf-card lf-enter lf-enter-delay-2 rounded-[22px] p-5">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2"><Leaf size={16} className="text-[hsl(147_48%_38%)]" /><h2 className="text-sm font-bold">What I remember</h2></div>
          <p className="text-[11px] text-[hsl(var(--muted-foreground))]">Preferences carry across turns automatically.</p>
        </div>
        <button data-testid="button-clear-memory" onClick={onClear} disabled={clearing || loading} className="group flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-[10px] font-semibold text-[hsl(var(--muted-foreground))] transition hover:bg-[hsl(var(--accent)/.1)] hover:text-[hsl(var(--accent-foreground))] disabled:opacity-45" title="Clear remembered preferences">
          <Trash2 size={13} /> {clearing ? 'Clearing' : 'Clear'}
        </button>
      </div>
      {error ? (
        <div data-testid="status-memory-error" className="flex gap-2 rounded-xl bg-[hsl(var(--accent)/.08)] p-3 text-[11px] text-[hsl(var(--muted-foreground))]"><CircleAlert size={14} className="shrink-0 text-[hsl(var(--accent))]" /> Memory is unavailable right now.</div>
      ) : loading ? (
        <div data-testid="status-memory-loading" className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-7 animate-pulse rounded-full bg-[hsl(var(--muted)/.7)]" />)}</div>
      ) : activeEntries.length === 0 ? (
        <div data-testid="memory-empty-state" className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-[hsl(var(--border))] px-4 py-5 text-center">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[hsl(var(--muted)/.6)]"><Leaf size={14} className="text-[hsl(var(--muted-foreground))]" /></div>
          <p className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))]">Nothing stored yet</p>
          <p className="text-[10px] text-[hsl(var(--muted-foreground)/.7)]">Mention your diet, cuisine, or city and I'll remember it.</p>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {activeEntries.map(({ label, value, color }) => (
              <div
                key={label}
                data-testid={`memory-${label.toLowerCase().replace(/\s/g, '-')}`}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-semibold ${color}`}
              >
                <span className="lf-mono text-[9px] uppercase tracking-[0.1em] opacity-70">{label}</span>
                <span>{value}</span>
              </div>
            ))}
          </div>
          {entries.filter((e) => e.value === null).length > 0 && (
            <p className="mt-3 text-[10px] text-[hsl(var(--muted-foreground)/.6)]">
              {entries.filter((e) => e.value === null).map((e) => e.label).join(' · ')} not set
            </p>
          )}
        </>
      )}
      {cleared && <div data-testid="status-memory-cleared" className="mt-3 flex items-center gap-2 text-[11px] font-semibold text-[hsl(147_48%_35%)]"><CircleCheck size={14} /> Memory cleared for this session.</div>}
    </section>
  );
}

function RecommendationCard({ item, index }: { item: Recommendation; index: number }) {
  const [showWhy, setShowWhy] = useState(false);
  const [selected, setSelected] = useState(false);
  return (
    <article data-testid={`card-recommendation-${item.id}`} className="lf-card group relative overflow-hidden rounded-[20px] p-4 transition duration-300 hover:-translate-y-0.5 sm:p-5">
      <div className="absolute right-0 top-0 h-24 w-24 rounded-bl-[80px] bg-[hsl(var(--secondary)/.12)] transition group-hover:bg-[hsl(var(--secondary)/.24)]" />
      <div className="relative flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[13px] bg-[hsl(var(--primary))] text-[hsl(var(--secondary))]"><span className="lf-display text-lg font-semibold">{String(index + 1).padStart(2, '0')}</span></div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div><h3 className="lf-display text-[21px] font-semibold leading-none">{item.name}</h3><div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px] text-[hsl(var(--muted-foreground))]"><span>{item.cuisine.join(' · ')}</span><span className="h-1 w-1 rounded-full bg-[hsl(var(--border))]" /><span>{item.diet.join(', ') || 'All diets'}</span></div></div>
            <div className="flex items-center gap-1 rounded-full bg-[hsl(var(--secondary)/.3)] px-2 py-1 text-[11px] font-bold"><Star size={12} fill="currentColor" /> {item.rating.toFixed(1)}</div>
          </div>
          <p className="mt-3 max-w-[550px] text-xs leading-5 text-[hsl(var(--muted-foreground))]">{item.description}</p>
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-[hsl(var(--border)/.7)] pt-3 text-[11px] font-semibold text-[hsl(var(--foreground)/.72)]">
            <span className="flex items-center gap-1.5"><MapPin size={13} className="text-[hsl(var(--accent))]" /> {item.distanceKm.toFixed(1)} km</span>
            <span className="flex items-center gap-1.5"><BadgeIndianRupee size={13} className="text-[hsl(147_48%_38%)]" /> {item.priceRange} · ₹{item.averagePrice}</span>
            <span className="flex items-center gap-1.5"><Zap size={13} className="text-[hsl(var(--secondary-foreground))]" /> {item.spiceLevel}</span>
            <span className="ml-auto flex items-center gap-1 text-[hsl(147_48%_35%)]"><span className="h-1.5 w-1.5 rounded-full bg-[hsl(147_48%_42%)]" /> {Math.round(item.score)} match</span>
          </div>
          <div className="mt-3 rounded-lg bg-[hsl(var(--muted)/.5)] px-3 py-2 text-[11px] leading-5 text-[hsl(var(--foreground)/.68)]"><span className="font-bold text-[hsl(var(--foreground))]">Why here:</span> {item.reason}</div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid={`button-why-${item.id}`}
              onClick={() => setShowWhy((current) => !current)}
              className="rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-[10px] font-bold text-[hsl(var(--foreground)/.72)] transition hover:border-[hsl(var(--accent)/.55)] hover:bg-[hsl(var(--accent)/.08)]"
            >
              {showWhy ? 'Hide score details' : 'Why this?'}
            </button>
            <button
              type="button"
              data-testid={`button-select-${item.id}`}
              aria-pressed={selected}
              onClick={() => setSelected((current) => !current)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[10px] font-bold transition ${selected ? 'bg-[hsl(147_48%_38%)] text-white' : 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:-translate-y-0.5'}`}
            >
              {selected && <Check size={12} />} {selected ? 'Selected' : 'Select'}
            </button>
          </div>
          {showWhy && (
            <div data-testid={`details-score-${item.id}`} className="mt-2 grid grid-cols-3 gap-2 text-[10px] text-[hsl(var(--muted-foreground))]">
              {Object.entries(item.scoreBreakdown).map(([factor, value]) => (
                <div key={factor} className="rounded-md bg-[hsl(var(--card)/.8)] px-2 py-1.5">
                  <div className="uppercase tracking-[0.08em]">{factor}</div>
                  <div className="mt-0.5 font-bold text-[hsl(var(--foreground))]">{Math.round(value * 100)} pts</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Trace panel — collapsed by default to keep internal reasoning off-screen.
// Professor / viva can expand it with one click.
// ---------------------------------------------------------------------------
function TracePanel({ trace, stats }: { trace: TraceStep[]; stats?: AgentResponse['stats'] }) {
  const [open, setOpen] = useState(false);

  return (
    <section className="lf-card lf-enter lf-enter-delay-3 overflow-hidden rounded-[22px]">
      <button
        type="button"
        data-testid="button-trace-toggle"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between border-b border-[hsl(var(--border)/.7)] px-5 py-4 text-left transition hover:bg-[hsl(var(--muted)/.3)]"
        aria-expanded={open}
      >
        <div>
          <div className="flex items-center gap-2">
            <RefreshCw size={15} className="text-[hsl(var(--accent))]" />
            <h2 className="text-sm font-bold">Decision / Agent trace</h2>
            <span className="lf-mono rounded-full bg-[hsl(var(--muted)/.7)] px-2 py-0.5 text-[9px] uppercase tracking-[0.1em] text-[hsl(var(--muted-foreground))]">
              {trace.length} steps
            </span>
          </div>
          <p className="mt-1 text-[11px] text-[hsl(var(--muted-foreground))]">
            PLAN → ACT → OBSERVE → DECIDE loop — expand for viva/professor review
          </p>
        </div>
        <ChevronDown
          size={16}
          className={`shrink-0 text-[hsl(var(--muted-foreground))] transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="p-3">
          {stats && (
            <div className="mb-3 flex flex-wrap gap-3 rounded-xl bg-[hsl(var(--muted)/.4)] px-4 py-3 text-[10px] font-semibold text-[hsl(var(--muted-foreground))]">
              <span>Searched: <strong className="text-[hsl(var(--foreground))]">{stats.searched}</strong></span>
              <span>After cuisine filter: <strong className="text-[hsl(var(--foreground))]">{stats.afterCuisine}</strong></span>
              <span>After diet filter: <strong className="text-[hsl(var(--foreground))]">{stats.afterDiet}</strong></span>
              <span>Elapsed: <strong className="text-[hsl(var(--foreground))]">{stats.elapsedMs}ms</strong></span>
            </div>
          )}
          {trace.length === 0
            ? <div data-testid="empty-trace" className="px-3 py-5 text-center text-xs text-[hsl(var(--muted-foreground))]">No trace to show yet.</div>
            : trace.map((step) => <TraceRow key={step.step} step={step} />)
          }
        </div>
      )}
    </section>
  );
}

function TraceRow({ step }: { step: TraceStep }) {
  const tone = step.type.toLowerCase();
  const typeStyle = tone.includes('plan') ? 'bg-[hsl(var(--secondary)/.32)] text-[hsl(25_29%_30%)]' : tone.includes('act') || tone === 'tool' ? 'bg-[hsl(198_43%_47%/.14)] text-[hsl(198_43%_36%)]' : tone.includes('observe') || tone === 'observation' ? 'bg-[hsl(147_48%_42%/.14)] text-[hsl(147_48%_33%)]' : tone === 'filter' ? 'bg-[hsl(277_24%_54%/.14)] text-[hsl(277_24%_35%)]' : 'bg-[hsl(var(--accent)/.14)] text-[hsl(var(--accent-foreground))]';
  return (
    <details data-testid={`trace-step-${step.step}`} className="group rounded-xl px-3 py-3 transition open:bg-[hsl(var(--muted)/.48)]">
      <summary data-testid={`button-trace-${step.step}`} className="flex cursor-pointer list-none items-center gap-3 [&::-webkit-details-marker]:hidden">
        <span className={`lf-mono w-[67px] shrink-0 rounded-md px-2 py-1 text-center text-[9px] font-medium uppercase tracking-[0.1em] ${typeStyle}`}>{step.type}</span>
        <span className="min-w-0 flex-1 truncate text-xs font-bold">{step.title}</span>
        <ChevronDown size={15} className="shrink-0 text-[hsl(var(--muted-foreground))] transition group-open:rotate-180" />
      </summary>
      <div className="ml-[79px] mt-3 border-l border-[hsl(var(--border))] pl-3 text-[11px] leading-5 text-[hsl(var(--muted-foreground))]">
        <p>{step.detail}</p>
        {step.tool && <div className="mt-2 flex items-center gap-1.5 font-semibold text-[hsl(var(--foreground)/.7)]"><Search size={12} /> {step.tool}</div>}
        {step.arguments && <div className="mt-1 rounded-lg bg-[hsl(var(--muted)/.5)] px-2.5 py-2 font-mono text-[10px] text-[hsl(var(--foreground)/.72)]">{JSON.stringify(step.arguments)}</div>}
        {step.result && <div className="mt-2 rounded-lg bg-[hsl(var(--card))] px-2.5 py-2 text-[10px] text-[hsl(var(--foreground)/.72)]">{step.result}</div>}
      </div>
    </details>
  );
}

function Router() {
  return (
    <ErrorBoundary>
      <Switch>
        <Route path="/" component={Home} />
        <Route component={Home} />
      </Switch>
    </ErrorBoundary>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;