"use client";

import React, { useEffect, useState } from 'react';
import styles from './explorer.module.css';

interface DecisionRecord {
  id: string;
  agent_identity: string;
  governance_status: string;
  rule_version_id: string;
  computed_output: any;
  cryptographic_receipt: string;
  execution_latency_ms: number;
  evaluated_at: string;
}

export default function DecisionExplorer() {
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReceipt, setSelectedReceipt] = useState<string | null>(null);
  const [trace, setTrace] = useState<any | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [verificationResult, setVerificationResult] = useState<'VALID' | 'TAMPERED' | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

  const fetchDecisions = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/govern/decisions`);
      if (!res.ok) throw new Error('Failed to fetch decisions');
      const data = await res.json();
      setDecisions(data.decisions || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setSimulating(true);
    try {
      const agents = ['Loan-Approval-AI', 'Sigma-Orchestrator', 'Risk-Evaluator-9', 'Compliance-Bot'];
      const rules = ['credit_policy_v1', 'risk_threshold_alpha', 'fraud_detection_gamma'];
      
      const payload = {
        agent_id: agents[Math.floor(Math.random() * agents.length)],
        rule_name: rules[Math.floor(Math.random() * rules.length)],
        context: { semantic_id: "doc_" + Math.random().toString(36).substr(2, 9) },
        input_data: { 
          credit_score: Math.floor(Math.random() * 500) + 300,
          transaction_amount: Math.floor(Math.random() * 10000),
          is_internal: Math.random() > 0.8
        }
      };

      const res = await fetch(`${API_URL}/api/v1/govern/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        await fetchDecisions();
      }
    } catch (e) {
      console.error('Simulation failed', e);
    } finally {
      setSimulating(false);
    }
  };

  useEffect(() => {
    fetchDecisions(); // Fetch initial state

    // Initialize Server-Sent Events connection
    const eventSource = new EventSource(`${API_URL}/api/v1/govern/decisions/stream`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.decisions) {
          setDecisions(data.decisions);
        }
      } catch (err) {
        console.error("Failed to parse SSE data", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      eventSource.close();
      // Optional: Logic to re-initialize EventSource after a delay could go here.
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const handleSelectDecision = async (receipt: string) => {
    setSelectedReceipt(receipt);
    setTrace(null);
    setVerificationResult(null);
    
    try {
      const res = await fetch(`${API_URL}/api/v1/govern/explain/${receipt}`);
      if (res.ok) {
        const data = await res.json();
        setTrace(data['Decision Trace']);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleVerify = async (receipt: string) => {
    setVerifying(true);
    setVerificationResult(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/govern/audit/${receipt}`);
      if (res.ok) {
        const data = await res.json();
        setVerificationResult(data.status);
      } else {
        setVerificationResult('TAMPERED');
      }
    } catch (e) {
      setVerificationResult('TAMPERED');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerTop}>
          <div className={styles.logoGroup}>
            <div className={styles.pulseDot}></div>
            <h1>Decision Explorer</h1>
            <span className={styles.badge}>Live Ledger</span>
          </div>
          <button 
            className={styles.simulateBtn} 
            onClick={handleSimulate}
            disabled={simulating}
          >
            {simulating ? 'Processing Action...' : '⚡ Trigger Agent Action'}
          </button>
        </div>
        <p className={styles.subtitle}>
          Databases store data. <strong>Tempus stores why systems act.</strong>
        </p>
      </header>

      <main className={styles.main}>
        <section className={styles.timelineSection}>
          <h2 className={styles.sectionTitle}>Global Decision Timeline</h2>
          {loading ? (
            <p className={styles.loading}>Loading decision ledger...</p>
          ) : error ? (
            <p className={styles.error}>{error}</p>
          ) : (
            <div className={styles.timeline}>
              {decisions.map((d) => (
                <div 
                  key={d.id} 
                  className={`${styles.timelineCard} ${selectedReceipt === d.cryptographic_receipt ? styles.activeCard : ''}`}
                  onClick={() => handleSelectDecision(d.cryptographic_receipt)}
                >
                  <div className={styles.cardHeader}>
                    <span className={styles.timestamp}>
                      {new Date(d.evaluated_at).toLocaleTimeString()}
                    </span>
                    <span className={styles.agentTag}>{d.agent_identity}</span>
                  </div>
                  <div className={styles.cardBody}>
                    <div className={styles.outcomeGroup}>
                      {d.computed_output?.approved === false ? (
                        <span className={styles.rejectTag}>BLOCKED</span>
                      ) : d.computed_output?.approved === true ? (
                        <span className={styles.approveTag}>APPROVED</span>
                      ) : d.computed_output?.error ? (
                        <span className={styles.rejectTag}>ERROR</span>
                      ) : (
                        <span className={styles.infoTag}>PROCESSED</span>
                      )}
                      <span className={styles.reasonText}>
                        {d.computed_output?.reason || 'Calculated output'}
                      </span>
                    </div>
                  </div>
                  <div className={styles.cardFooter}>
                    <span className={styles.latency}>{d.execution_latency_ms.toFixed(2)} ms</span>
                    <span className={styles.hashPreview}>{d.cryptographic_receipt.substring(0, 12)}...</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className={styles.inspectorSection}>
          {selectedReceipt ? (
            <div className={styles.inspector}>
              <div className={styles.inspectorHeader}>
                <h2>Sello Criptográfico (HMAC-SHA256)</h2>
                <button 
                  className={styles.verifyBtn} 
                  onClick={() => handleVerify(selectedReceipt)}
                  disabled={verifying}
                >
                  {verifying ? 'Auditing...' : 'Ejecutar Auditoría Matemática'}
                </button>
                <p className={styles.helperText}>Checks the database record against its digital signature to mathematically prove no hacker or rogue admin has altered it.</p>
                {verificationResult === 'VALID' && (
                  <div className={styles.validBadge}>✓ Sello Auténtico y Verificado</div>
                )}
                {verificationResult === 'TAMPERED' && (
                  <div className={styles.invalidBadge}>
                    <span className={styles.alertIcon}>🚨</span>
                    ALERTA ROJA: MANIPULACIÓN DETECTADA
                  </div>
                )}
              </div>
              
              <div className={styles.hashBox}>
                <code>{selectedReceipt}</code>
              </div>

              {trace ? (
                <div className={styles.traceView}>
                  <h3>Causal Trace</h3>
                  <div className={styles.traceBlock}>
                    <strong>Agent:</strong> {trace.Agent}
                  </div>
                  <div className={styles.traceBlock}>
                    <strong>Governance Rule:</strong> {trace['Rule Version']}
                  </div>
                  <div className={styles.traceBlock}>
                    <strong>Input Context:</strong>
                    <pre>{JSON.stringify(trace.Input, null, 2)}</pre>
                  </div>
                  <div className={styles.traceBlock}>
                    <strong>Deterministic Output:</strong>
                    <pre>{JSON.stringify(trace.Output, null, 2)}</pre>
                  </div>
                </div>
              ) : (
                <p className={styles.loading}>Reconstructing decision trace...</p>
              )}
            </div>
          ) : (
            <div className={styles.emptyInspector}>
              <div className={styles.emptyIcon}>🔍</div>
              <p><strong>The Black Box is now open.</strong><br/><br/> Select a decision from the timeline to see exactly why the AI acted, and mathematically verify that the record is authentic.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
