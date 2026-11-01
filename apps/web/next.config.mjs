/** @type {import('next').NextConfig} */
const nextConfig = {
  // Cada respuesta de la entrevista de perfil se extrae con el modelo dentro de la petición
  // (ADR-0020): con el modelo local tarda hasta un minuto y el proxy corta a los 30 s por defecto.
  experimental: { proxyTimeout: 180_000 },
  // La web llama a /api/... y Next lo reenvía a la API: sin CORS y sin URL en el cliente.
  async rewrites() {
    const api = process.env.API_URL ?? "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${api}/:path*` }];
  },
};
export default nextConfig;
