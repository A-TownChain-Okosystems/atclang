# Security Policy — atclang

**Klassifizierung:** CORE · **Maturity:** R4 · **Security-Level:** S4 (S-Klasse gemaess ATC-STD-202)
**Criticality:** critical · **Standard:** ATC-STD-203 (Repository Security & Release)

## Melde-und-Offenlegungspolitik

1. Schwachstellen werden NICHT oeffentlich als Issue gemeldet, sondern direkt
   an den Owner (ShivaCoreDev) kommuniziert.
2. Sicherheitsrelevante Aenderungen laufen als `security(...)`-Commits und
   werden im zentralen DECISIONS_REGISTER dokumentiert.
3. Kritische Vorkommnisse folgen dem Emergency-Prozess (ATC-STD-000 §32):
   Temporary Decision → Implementation → Formal Standard Revision.

## Geltende Regeln

- Keine Secrets/Keys/Credentials in diesem Repository (Hygiene-Regel V-11).
- Abhaengigkeiten: Third-Party nur nach Freigabe (ATC-STD-203 Dependency
  Policy; AD-021: Python nur AI-Layer/Tooling, nie Konsensus-Ausfuehrung).
- Release-Gates GATE-001…GATE-010 (ATC-STD-203) vor jedem Release ab R3.
- Lizenzmodell: ATC-LIC/ATS-LIC, ATVM blockt unlizentierte Ausfuehrung.

## Vertrauensgrenzen

Kernel (atc-shivacore) bleibt von Services strikt getrennt (AD-012/028);
Blockchain-Konsensus laeuft ausschliesslich auf verifiziertem ATVM-Code
(AD-022: Compiler erzeugt, Verifier entscheidet, ATVM fuehrt aus).
