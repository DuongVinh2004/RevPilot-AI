/**
 * RevPilot AI — Web Frontend Application Bootstrap
 * Conforms to:
 * - docs/28-frontend/FRONTEND-SPEC.md
 * - WCAG 2.2 AA Accessibility Navigation
 */

import { ApprovalCenterComponent } from "./components/ApprovalCenter";
import { AnomalyDashboardComponent } from "./components/AnomalyDashboard";
import { KillSwitchComponent } from "./components/KillSwitch";

document.addEventListener("DOMContentLoaded", async () => {
  // Initialize components
  const approvalCenter = new ApprovalCenterComponent("approval-queue-container");
  const anomalyDashboard = new AnomalyDashboardComponent("anomaly-list-container");
  const killSwitch = new KillSwitchComponent("killswitch-container");

  await approvalCenter.render();
  await anomalyDashboard.render();
  killSwitch.render();

  // Tab Navigation Handling
  const navApprovals = document.getElementById("nav-approvals");
  const navAnomalies = document.getElementById("nav-anomalies");
  const navKillswitch = document.getElementById("nav-killswitch");

  const secApprovals = document.getElementById("section-approvals");
  const secAnomalies = document.getElementById("section-anomalies");
  const secKillswitch = document.getElementById("section-killswitch");

  function switchTab(activeBtn: HTMLElement, activeSec: HTMLElement) {
    [navApprovals, navAnomalies, navKillswitch].forEach((btn) => {
      btn?.classList.remove("active");
      btn?.removeAttribute("aria-current");
    });
    [secApprovals, secAnomalies, secKillswitch].forEach((sec) => {
      sec?.classList.add("hidden");
    });

    activeBtn.classList.add("active");
    activeBtn.setAttribute("aria-current", "page");
    activeSec.classList.remove("hidden");

    // Announce for screen reader
    const announcer = document.getElementById("status-announcer");
    if (announcer) {
      announcer.textContent = `Navigated to ${activeBtn.textContent?.trim()}`;
    }
  }

  navApprovals?.addEventListener("click", () => switchTab(navApprovals, secApprovals!));
  navAnomalies?.addEventListener("click", () => switchTab(navAnomalies, secAnomalies!));
  navKillswitch?.addEventListener("click", () => switchTab(navKillswitch, secKillswitch!));
});
