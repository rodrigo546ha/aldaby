import { NextResponse, type NextRequest } from "next/server";

// Beta privada (ADR-0028): sin cookie de sesión, a la página de acceso. La API comprueba la sesión
// en cada petición; esto solo evita enseñar páginas vacías. En el Mac, HOUSEFINDER_DEV_ORG=1
// trabaja sin cuenta con la organización local de desarrollo.
export function middleware(request: NextRequest) {
  if (process.env.HOUSEFINDER_DEV_ORG === "1" || request.cookies.has("hf_sesion")) {
    return NextResponse.next();
  }
  const url = request.nextUrl.clone();
  url.pathname = "/acceso";
  url.search = `?siguiente=${encodeURIComponent(request.nextUrl.pathname)}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!api|_next|acceso|favicon.ico).*)"],
};
