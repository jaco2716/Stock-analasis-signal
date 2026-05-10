import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE, verifySessionToken } from "@/lib/auth";

export const middleware = async (request: NextRequest) => {
  const { pathname } = request.nextUrl;
  if (pathname === "/login") return NextResponse.next();

  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (await verifySessionToken(token)) return NextResponse.next();

  const url = request.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("from", pathname + request.nextUrl.search);
  return NextResponse.redirect(url);
};

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
