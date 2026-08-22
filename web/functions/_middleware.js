// Cloudflare Pages Edge Middleware
// Automatically redirects any traffic hitting *.pages.dev directly to the custom canonical domain.

export async function onRequest(context) {
  const url = new URL(context.request.url);

  // If accessed directly via *.pages.dev (and not localhost), redirect to official custom domain
  if (url.hostname.endsWith('.pages.dev') && !url.hostname.includes('localhost')) {
    url.hostname = 'status.mimamita.site';
    return Response.redirect(url.toString(), 301);
  }

  return context.next();
}
