import { NextRequest, NextResponse } from "next/server";

function getCookie(request: NextRequest, name: string): string | undefined {
  return request.cookies.get(name)?.value;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const supabaseAuthCookie = request.cookies.getAll().find((c) => c.name.startsWith("sb-"));
  const hasSession = !!supabaseAuthCookie?.value;
  const userType = getCookie(request, "nh-user-type");
  const onboarded = getCookie(request, "nh-onboarded");
  const expertStatus = getCookie(request, "nh-expert-status");

  // Public pages: redirect to dashboard if already logged in
  if (pathname === "/login" || pathname === "/register") {
    if (hasSession && userType && onboarded === "1") {
      const home =
        userType === "EXPERT" ? "/expert/dashboard" :
        userType === "ADMIN" ? "/admin/dashboard" :
        "/user/dashboard";
      return NextResponse.redirect(new URL(home, request.url));
    }
    return NextResponse.next();
  }

  // Onboarding page
  if (pathname === "/onboarding") {
    if (!hasSession) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
    if (onboarded === "1" && userType) {
      const home =
        userType === "EXPERT" ? "/expert/dashboard" :
        userType === "ADMIN" ? "/admin/dashboard" :
        "/user/dashboard";
      return NextResponse.redirect(new URL(home, request.url));
    }
    return NextResponse.next();
  }

  // Protected routes: require session
  if (!hasSession) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Not onboarded yet
  if (onboarded !== "1") {
    return NextResponse.redirect(new URL("/onboarding", request.url));
  }

  // Role-based access
  if (pathname.startsWith("/expert/")) {
    if (userType !== "EXPERT") {
      const home = userType === "ADMIN" ? "/admin/dashboard" : "/user/dashboard";
      return NextResponse.redirect(new URL(home, request.url));
    }
  }

  if (pathname.startsWith("/admin/")) {
    if (userType !== "ADMIN") {
      const home = userType === "EXPERT" ? "/expert/dashboard" : "/user/dashboard";
      return NextResponse.redirect(new URL(home, request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/login",
    "/register",
    "/onboarding",
    "/user/:path*",
    "/expert/:path*",
    "/admin/:path*",
  ],
};
