/** @type {import('next').NextConfig} */
const nextConfig = {
  // La web llama a /api/... y Next lo reenvía a la API: sin CORS y sin URL en el cliente.
  async rewrites() {
    const api = process.env.API_URL ?? "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${api}/:path*` }];
  },
};
export default nextConfig;
