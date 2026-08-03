import type { Plugin } from "vite";
import { defineConfig as defineLovableConfig } from "@lovable.dev/vite-tanstack-config";

/**
 * Temporary diagnostics: prove whether /api requests hit Vite, the proxy, or
 * fall through to TanStack Start's catch-all SSR handler.
 */
function apiProxyProbePlugin(): Plugin {
  return {
    name: "omni-api-proxy-probe",
    configureServer(server) {
      // Runs BEFORE Vite internal middlewares (including server.proxy).
      server.middlewares.use((req, res, next) => {
        const url = req.originalUrl ?? req.url ?? "";
        if (!url.startsWith("/api")) {
          next();
          return;
        }

        const start = Date.now();
        console.log(
          `[api-probe:in] ${req.method} ${url} content-type=${req.headers["content-type"] ?? "-"} content-length=${req.headers["content-length"] ?? "-"} origin=${req.headers.origin ?? "-"} referer=${req.headers.referer ?? "-"} ua=${req.headers["user-agent"] ?? "-"} sec-fetch-site=${req.headers["sec-fetch-site"] ?? "-"} sec-fetch-mode=${req.headers["sec-fetch-mode"] ?? "-"} sec-fetch-dest=${req.headers["sec-fetch-dest"] ?? "-"}`,
        );

        req.on("aborted", () => {
          console.error(`[api-probe:aborted] ${req.method} ${url} after ${Date.now() - start}ms`);
        });

        res.on("finish", () => {
          console.log(
            `[api-probe:out] ${req.method} ${url} -> ${res.statusCode} (${Date.now() - start}ms) content-type=${res.getHeader("content-type") ?? "-"}`,
          );
        });
        res.on("close", () => {
          if (!res.writableEnded) {
            console.error(`[api-probe:res-close-early] ${req.method} ${url} after ${Date.now() - start}ms`);
          }
        });

        next();
      });

      // Runs AFTER internal middlewares (proxy) and BEFORE/with late plugins.
      // If this logs for /api, the Vite proxy did NOT handle the request.
      return () => {
        server.middlewares.use((req, res, next) => {
          const url = req.originalUrl ?? req.url ?? "";
          if (url.startsWith("/api")) {
            console.warn(
              `[api-probe:fallback] ${req.method} ${url} reached post-proxy middleware — Vite proxy did NOT consume this request. Next handler is typically TanStack Start SSR catch-all.`,
            );
          }
          next();
        });
      };
    },
  };
}

export default defineLovableConfig({
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
  plugins: [apiProxyProbePlugin()],
  vite: {
    server: {
      // Same-origin /api/* → FastAPI. Must be valid JSON/JS or the entire config fails to load.
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyReq, req) => {
              console.log(
                `[api-probe:proxyReq] forwarding ${req.method} ${req.url} -> http://127.0.0.1:8000${req.url}`,
              );
            });
            proxy.on("proxyRes", (proxyRes, req) => {
              console.log(
                `[api-probe:proxyRes] ${req.method} ${req.url} <- upstream ${proxyRes.statusCode}`,
              );
            });
            proxy.on("error", (err, req) => {
              console.error(
                `[api-probe:proxyError] ${req.method} ${req.url}:`,
                err.message,
              );
            });
          },
        },
      },
    },
  },
});
