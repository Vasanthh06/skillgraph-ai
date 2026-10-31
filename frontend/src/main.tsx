import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider, ScrollRestoration } from "react-router-dom";
import { ThemeProvider } from "./store/theme";
import { NavigationProvider } from "./store/navigation";
import App from "./App";
import { AuthProvider } from "./store/auth";
import { DirtyProvider } from "./store/dirty";
import { NoticeProvider } from "./store/notice";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

function Providers() {
  return <ThemeProvider><NoticeProvider><DirtyProvider><AuthProvider><NavigationProvider><App /><ScrollRestoration /></NavigationProvider></AuthProvider></DirtyProvider></NoticeProvider></ThemeProvider>;
}
const router = createBrowserRouter([{path: "*", element: <Providers />}]);
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider></React.StrictMode>,
);
