"use client";

import Link from "next/link";
import { IconShieldLock, IconBrain, IconDatabaseLeak } from "@tabler/icons-react";
import styles from "./landing.module.css";

export default function LandingPage() {
  return (
    <main className={styles.container}>
      {/* Background Ambience */}
      <div className={styles.glow1} />
      <div className={styles.glow2} />

      <div className={styles.content}>
        {/* Hero Section */}
        <span className={styles.badge}>MICA & AI Act Compliant</span>
        <h1 className={styles.title}>
          The <span className={styles.highlight}>Immune System</span><br />
          For Corporate AI
        </h1>
        <p className={styles.subtitle}>
          Tempus DDB is an immutable, cryptographically verifiable ledger that sits between your AI Agents and reality. Audit exactly <b>why</b> your AI acted, down to the byte.
        </p>

        {/* Call to Actions */}
        <div className={styles.actions}>
          <Link href="/explorer" className={styles.btnPrimary}>
            Launch The Black Box ⚡
          </Link>
          <a href="https://github.com/jpatron92/DBD" target="_blank" rel="noopener noreferrer" className={styles.btnSecondary}>
            View GitHub
          </a>
        </div>

        {/* Feature Grid */}
        <div className={styles.features}>
          <div className={styles.featureCard}>
            <IconShieldLock size={32} className={styles.featureIcon} />
            <h3 className={styles.featureTitle}>Cryptographic Receipts</h3>
            <p className={styles.featureDesc}>
              Every AI action generates a unique digital fingerprint (Cryptographic Receipt). A mathematical guarantee that decisions weren't tampered with by hackers or rogue employees.
            </p>
          </div>
          
          <div className={styles.featureCard}>
            <IconDatabaseLeak size={32} className={styles.featureIcon} />
            <h3 className={styles.featureTitle}>Deep Immutability</h3>
            <p className={styles.featureDesc}>
              Records are locked at the database core. Not even system administrators can quietly alter historical decisions to cover up mistakes.
            </p>
          </div>

          <div className={styles.featureCard}>
            <IconBrain size={32} className={styles.featureIcon} />
            <h3 className={styles.featureTitle}>Causal Tracing</h3>
            <p className={styles.featureDesc}>
              Stop trusting Black Boxes. Tempus visualizes the exact deterministic inputs, rules, and semantic contexts that led to any AI outcome.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
