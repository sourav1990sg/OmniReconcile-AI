/**
 * Browser compatibility probe — does NOT modify application source.
 * Compares Chromium (Chrome/Edge) vs Firefox request headers & fetch outcomes.
 */
import { chromium, firefox } from "playwright-core";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const BASE = process.env.DEBUG_BASE || "http://localhost:8080";
const REPORT = [];

function log(section, data) {
  const entry = { section, at: new Date().toISOString(), data };
  REPORT.push(entry);
  console.log(`\n=== ${section} ===`);
  console.log(typeof data === "string" ? data : JSON.stringify(data, null, 2));
}

async function captureBrowser(label, browserType, launchOpts) {
  const result = {
    label,
    launchOpts: { ...launchOpts, executablePath: launchOpts.executablePath || launchOpts.channel },
    navError: null,
    runtime: null,
    requests: [],
    failures: [],
    responses: [],
    consoles: [],
    pageErrors: [],
  };

  let browser;
  try {
    browser = await browserType.launch(launchOpts);
  } catch (e) {
    result.navError = `launch failed: ${e.message}`;
    log(`${label}:launch`, result.navError);
    return result;
  }

  const context = await browser.newContext();
  const page = await context.newPage();

  // Capture exact request headers for /api/*
  await page.route("**/api/**", async (route, request) => {
    const headers = request.headers();
    result.requests.push({
      method: request.method(),
      url: request.url(),
      headers: {
        "content-type": headers["content-type"] || null,
        origin: headers["origin"] || null,
        referer: headers["referer"] || null,
        "content-length": headers["content-length"] || null,
        "sec-fetch-site": headers["sec-fetch-site"] || null,
        "sec-fetch-mode": headers["sec-fetch-mode"] || null,
        "sec-fetch-dest": headers["sec-fetch-dest"] || null,
        "sec-fetch-storage-access": headers["sec-fetch-storage-access"] || null,
        "access-control-request-private-network":
          headers["access-control-request-private-network"] || null,
        "access-control-request-headers": headers["access-control-request-headers"] || null,
        "user-agent": headers["user-agent"] || null,
        accept: headers["accept"] || null,
        "accept-language": headers["accept-language"] || null,
      },
      postDataLength: request.postDataBuffer()?.length ?? null,
    });
    await route.continue();
  });

  page.on("requestfailed", (req) => {
    if (req.url().includes("/api") || req.url().includes(":8000")) {
      result.failures.push({
        method: req.method(),
        url: req.url(),
        errorText: req.failure()?.errorText || null,
      });
    }
  });

  page.on("response", async (res) => {
    if (res.url().includes("/api") || res.url().includes(":8000")) {
      result.responses.push({
        status: res.status(),
        url: res.url(),
        contentType: res.headers()["content-type"] || null,
      });
    }
  });

  page.on("console", (msg) => {
    result.consoles.push({ type: msg.type(), text: msg.text().slice(0, 300) });
  });

  page.on("pageerror", (err) => {
    result.pageErrors.push(err.message);
  });

  try {
    await page.goto(BASE, { waitUntil: "domcontentloaded", timeout: 45000 });
  } catch (e) {
    result.navError = e.message;
    await browser.close();
    log(`${label}:nav`, result);
    return result;
  }

  result.runtime = await page.evaluate(async () => {
    const info = {
      href: location.href,
      origin: location.origin,
      protocol: location.protocol,
      userAgent: navigator.userAgent,
      serviceWorkerControlled: !!navigator.serviceWorker?.controller,
      serviceWorkerRegs: [],
      caches: [],
      crossOriginIsolated: crossOriginIsolated,
      fetchExists: typeof fetch === "function",
      tests: {},
    };

    try {
      const regs = await navigator.serviceWorker?.getRegistrations?.();
      info.serviceWorkerRegs = (regs || []).map((r) => ({
        scope: r.scope,
        active: !!r.active,
        scriptURL: r.active?.scriptURL || r.installing?.scriptURL || null,
      }));
    } catch (e) {
      info.serviceWorkerRegsError = String(e);
    }

    try {
      info.caches = await caches.keys();
    } catch (e) {
      info.cachesError = String(e);
    }

    async function tryFetch(name, url, init) {
      try {
        const r = await fetch(url, init);
        const ct = r.headers.get("content-type");
        const body = (await r.text()).slice(0, 120);
        return { ok: r.ok, status: r.status, contentType: ct, body };
      } catch (e) {
        return { error: String(e), name: e.name, message: e.message };
      }
    }

    const fd = () => {
      const form = new FormData();
      form.append(
        "pos_files",
        new File(
          ["Aggregator Order No.,My amount,Date,Outlet Name\n1001,100.50,2026-01-01,Shop 1\n"],
          "pos_batch.csv",
          { type: "text/csv" },
        ),
      );
      form.append(
        "agg_files",
        new File(
          [
            "Order No,Net Payable Amount (after TCS and TDS deduction) Y = W - X1 - X2\n1001,95.00\n",
          ],
          "swiggy_settlement.csv",
          { type: "text/csv" },
        ),
      );
      return form;
    };

    info.tests.healthRelative = await tryFetch("health", "/api/health");
    info.tests.reconcileRelative = await tryFetch("reconcile", "/api/reconcile", {
      method: "POST",
      body: fd(),
    });
    info.tests.healthLoopback = await tryFetch("health8000", "http://127.0.0.1:8000/api/health");
    info.tests.healthLocalhost8000 = await tryFetch(
      "healthLocalhost8000",
      "http://localhost:8000/api/health",
    );
    info.tests.reconcileAbsoluteLoopback = await tryFetch(
      "reconcileAbs",
      "http://127.0.0.1:8000/api/reconcile",
      { method: "POST", body: fd() },
    );
    info.tests.reconcileAbsoluteLocalhost = await tryFetch(
      "reconcileAbsLocalhost",
      "http://localhost:8000/api/reconcile",
      { method: "POST", body: fd() },
    );

    return info;
  });

  await browser.close();
  log(`${label}:summary`, {
    href: result.runtime?.href,
    ua: result.runtime?.userAgent?.slice(0, 120),
    sw: result.runtime?.serviceWorkerRegs,
    caches: result.runtime?.caches,
    tests: result.runtime?.tests,
    apiRequests: result.requests,
    failures: result.failures,
    responses: result.responses,
    consoleErrors: result.consoles.filter((c) => c.type === "error"),
    pageErrors: result.pageErrors,
    navError: result.navError,
  });
  return result;
}

const chromeClean = await captureBrowser("chrome-clean-profile", chromium, {
  channel: "chrome",
  headless: false,
  args: ["--disable-extensions", "--disable-component-extensions-with-background-pages"],
});

const edgeClean = await captureBrowser("edge-clean-profile", chromium, {
  channel: "msedge",
  headless: false,
  args: ["--disable-extensions"],
});

// Real Chrome user profile (closest to "my Chrome")
const chromeUserData = path.join(os.homedir(), "AppData", "Local", "Google", "Chrome", "User Data");
let chromeReal = null;
if (fs.existsSync(chromeUserData)) {
  try {
    const tmpCopyHint = path.join(os.tmpdir(), "omni-chrome-debug-profile");
    // Use launchPersistentContext against a clone is hard; try channel with ignoreDefaultArgs
    // Persistent context with Default profile often fails if Chrome is already open.
    const context = await chromium.launchPersistentContext(chromeUserData, {
      channel: "chrome",
      headless: false,
      args: ["--profile-directory=Default", "--disable-extensions"],
      timeout: 20000,
    });
    // If this worked Chrome wasn't locking the profile
    await context.close();
    log("chrome-real-profile", "Opened Default profile with --disable-extensions (Chrome was not locking profile)");
  } catch (e) {
    log("chrome-real-profile", {
      note: "Could not attach to real Chrome Default profile (usually because Chrome is already running).",
      error: e.message,
      implication:
        "Automation uses a clean profile; your real Chrome/Edge may have extensions, flags, or Local Network Access decisions that clean automation does not.",
    });
  }
}

let firefoxResult = null;
try {
  firefoxResult = await captureBrowser("firefox-system", firefox, {
    executablePath: "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
    headless: false,
  });
} catch (e) {
  log("firefox-system", `failed: ${e.message}`);
}

// Diff Chromium vs Firefox request headers for POST /api/reconcile
function firstPost(requests) {
  return (requests || []).find((r) => r.method === "POST" && r.url.includes("/api/reconcile"));
}

const diff = {
  chromePost: firstPost(chromeClean.requests),
  edgePost: firstPost(edgeClean.requests),
  firefoxPost: firstPost(firefoxResult?.requests),
  chromeRelativeOk: chromeClean.runtime?.tests?.reconcileRelative,
  edgeRelativeOk: edgeClean.runtime?.tests?.reconcileRelative,
  firefoxRelativeOk: firefoxResult?.runtime?.tests?.reconcileRelative,
  chromeFailures: chromeClean.failures,
  edgeFailures: edgeClean.failures,
  firefoxFailures: firefoxResult?.failures,
};

log("DIFF", diff);

const outPath = path.resolve("browser-compat-report.json");
fs.writeFileSync(outPath, JSON.stringify({ BASE, REPORT, diff }, null, 2));
console.log(`\nWrote ${outPath}`);
