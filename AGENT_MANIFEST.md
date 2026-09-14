# AGENT_MANIFEST.md
> **Registry-Stand (GENERIERT aus `atc-standards/registry/standards.yaml`):** 505 Standards — 505 APPROVED · 0 CANDIDATE · 75 Familien · Stand 2026-09-14 · SSOT-Sync erforderlich.
> Letzte Aktualisierung dieses Manifests muss bei Registry-Änderungen durch den zentralen Generator erfolgen. Historische Stände sind nicht normativ.

## ⚖️ Standard-Compliance-Mandat (verbindlich — ATC-AAS-003/AAS-004, AI-DEV-001 §6)

> **Der zuständige Agent MUSS sämtliche anwendbaren Standards der zentralen Registry einhalten und umsetzen.** Keine statische Kopie des vollständigen Registry-Inhalts ist normativ.

1. **Vollmandat mit Anwendbarkeit:** Registry-Standards sind für den Agenten verbindlich, gestuft nach Anwendbarkeit (MANDATORY, CONDITIONAL, REFERENCE, NOT_APPLICABLE mit Begründung).
2. **Dynamische Bindung:** `atc-standards/registry/standards.yaml` ist SSOT. Neue APPROVED-Standards werden ab Freigabe verbindlich; dieses Manifest darf keine veralteten Registry-Zahlen oder historischen Statuswerte als aktuell ausgeben.
3. **Umsetzungspflicht:** Repo-Manifeste, AGENTS.md, Audit-Records, Tests und CI-Gates müssen mit der zentralen Registry konsistent sein.
4. **Konfliktregel:** Bei Konflikten gilt die Rangfolge der aktuellen APPROVED-Verfassung; Konflikte werden als Finding dokumentiert.
5. **Nachweis:** Agenten-Aktionen werden über AUD-Records und Evidenz nachgewiesen.
6. **CI-Enforcement:** Generator/Validator müssen Registry-Drift erkennen und den Build bei einem inkonsistenten generierten Stand blockieren.

## Repositories

Die historische Repository-Liste in diesem Manifest ist Archivmaterial. Der aktuelle Organisationsbestand ist ausschließlich aus den zentralen Governance-SSOTs (`atc-standards/registry/repositories.yaml` und `.github/ai/org-scope.yaml`) abzuleiten.

## Governance

**Kanonische Verfassung:** ATC-STD-000 v1.3.0 (APPROVED). Versionen und Statuswerte dürfen nicht aus historischen Manifestabschnitten übernommen werden.
