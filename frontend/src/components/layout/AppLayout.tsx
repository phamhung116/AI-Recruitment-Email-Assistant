import { Outlet } from "react-router-dom";

import { ToastViewport } from "@/components/shared/ToastViewport";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppLayout() {
    return (
        <div className="min-h-screen bg-background">
            <div className="flex min-h-screen">
                <Sidebar />
                <div className="flex min-w-0 flex-1 flex-col">
                    <Topbar />
                    <main className="flex-1 p-4 sm:p-6">
                        <Outlet />
                    </main>
                </div>
            </div>
            <ToastViewport />
        </div>
    );
}
