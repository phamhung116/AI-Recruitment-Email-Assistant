import { spawn } from "node:child_process";
import { rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const frontendRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const backendRoot = path.resolve(frontendRoot, "../backend");
const virtualEnvPython = process.platform === "win32"
    ? path.join(backendRoot, ".venv", "Scripts", "python.exe")
    : path.join(backendRoot, ".venv", "bin", "python");
const pythonExecutable = process.env.PYTHON_EXECUTABLE || (existsSync(virtualEnvPython) ? virtualEnvPython : "python");
const viteCli = path.join(frontendRoot, "node_modules", "vite", "bin", "vite.js");
const playwrightCli = path.join(frontendRoot, "node_modules", "@playwright", "test", "cli.js");
const e2eDatabase = path.join(backendRoot, "..", ".staging", "e2e", "recruitment-e2e.sqlite3");
const serverProcesses = [];

function startProcess(command, args, options) {
    const child = spawn(command, args, {
        shell: false,
        stdio: "inherit",
        windowsHide: true,
        ...options,
    });
    serverProcesses.push(child);
    return child;
}

async function waitForUrl(url, child, timeoutMs = 60_000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        if (child.exitCode !== null) {
            throw new Error(`Test server exited before ${url} became ready (code ${child.exitCode}).`);
        }
        try {
            const response = await fetch(url);
            if (response.ok) return;
        } catch {
            // The server is still starting.
        }
        await new Promise((resolve) => setTimeout(resolve, 250));
    }
    throw new Error(`Timed out waiting for ${url}.`);
}

async function stopProcess(child) {
    if (child.exitCode !== null || child.pid === undefined) return;
    child.kill();
    const closed = await Promise.race([
        new Promise((resolve) => child.once("close", () => resolve(true))),
        new Promise((resolve) => setTimeout(() => resolve(false), 3_000)),
    ]);
    if (!closed && process.platform === "win32") {
        await new Promise((resolve) => {
            const killer = spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], {
                stdio: "ignore",
                windowsHide: true,
            });
            killer.once("close", resolve);
        });
    }
}

async function main() {
    const backend = startProcess(pythonExecutable, ["-m", "scripts.run_e2e_server"], {
        cwd: backendRoot,
    });
    const frontend = startProcess(process.execPath, [viteCli, "--configLoader", "runner", "--host", "127.0.0.1", "--port", "14173", "--strictPort"], {
        cwd: frontendRoot,
        env: {
            ...process.env,
            VITE_API_BASE_URL: "http://127.0.0.1:18000",
        },
    });

    try {
        await Promise.all([
            waitForUrl("http://127.0.0.1:18000/health", backend),
            waitForUrl("http://127.0.0.1:14173", frontend),
        ]);
        const runner = spawn(process.execPath, [playwrightCli, "test", ...process.argv.slice(2)], {
            cwd: frontendRoot,
            shell: false,
            stdio: "inherit",
            windowsHide: true,
        });
        const exitCode = await new Promise((resolve) => runner.once("close", (code) => resolve(code ?? 1)));
        process.exitCode = exitCode;
    } finally {
        await Promise.all(serverProcesses.map(stopProcess));
        await rm(e2eDatabase, { force: true });
    }
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
