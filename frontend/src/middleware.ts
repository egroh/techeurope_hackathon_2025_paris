// Read more about middleware here: https://nextjs.org/docs/app/building-your-application/routing/middleware
import { NextRequest, NextResponse } from "next/server";

// This environment variable is for the Next.js server (middleware)
// to know where to proxy HTTP requests. It should be the FULL BASE URL.
const PROXY_TARGET_BASE_URL =
  process.env.BACKEND_API_PROXY_URL || "http://localhost:8000"; // Fallback

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (pathname.startsWith("/api/")) {
    // Construct the target URL by appending the current path and search to the proxy base URL
    const targetUrl = new URL(pathname + search, PROXY_TARGET_BASE_URL);
    console.log(
      `[Middleware] Rewriting ${request.url} to ${targetUrl.toString()}`
    );
    return NextResponse.rewrite(targetUrl, { request }); // Pass original request for headers
  }

  return NextResponse.next(); // Allow other requests to pass through
}

// Updated config export for the matcher
export const matcher = [
  // This matcher targets all requests starting with /api/
  "/api/:path*",
];
