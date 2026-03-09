
export default function Pitch() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#020617] text-white p-8">
      <h1 className="text-5xl font-bold mb-4 text-center tracking-tight">The Black Box for AI Agents.</h1>
      <p className="text-xl text-[#94a3b8] mb-12 text-center max-w-2xl">
        AI models hallucinate. Software shouldn&apos;t. Tempus is the definitive ledger that proves exactly <strong className="text-white">why</strong> an agent took an action.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full max-w-5xl">
        <div className="bg-[rgba(255,255,255,0.02)] p-6 rounded-xl border border-[rgba(255,255,255,0.05)]">
          <h3 className="text-[#10b981] font-bold mb-2">1. Agent acts</h3>
          <p className="text-sm text-[#94a3b8]">The AI proposes a decision based on its context.</p>
        </div>
        <div className="bg-[rgba(255,255,255,0.02)] p-6 rounded-xl border border-[rgba(255,255,255,0.05)]">
          <h3 className="text-[#38bdf8] font-bold mb-2">2. Tempus validates</h3>
          <p className="text-sm text-[#94a3b8]">Our deterministic Rust engine evaluates the action against hard corporate rules.</p>
        </div>
        <div className="bg-[rgba(255,255,255,0.02)] p-6 rounded-xl border border-[rgba(255,255,255,0.05)]">
          <h3 className="text-[#818cf8] font-bold mb-2">3. Sello Criptográfico</h3>
          <p className="text-sm text-[#94a3b8]">The causal chain is sealed with HMAC-SHA256 forever. Ready for rigorous corporate <b>auditorías</b>.</p>
        </div>
      </div>
    </div>
  );
}
