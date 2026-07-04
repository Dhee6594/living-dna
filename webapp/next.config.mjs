/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Reuse the existing Python genome API — never duplicate backend logic.
    const api = process.env.DNA_API_URL ?? "http://127.0.0.1:8077";
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};

export default nextConfig;
