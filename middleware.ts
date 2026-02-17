export { default } from "next-auth/middleware";

export const config = {
  matcher: [
    "/((?!login|register|api/auth|api/debug|_next/static|_next/image|favicon.ico).*)",
  ],
};
