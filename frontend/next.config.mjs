/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const defaultBackend =
      process.env.NODE_ENV === "development"
        ? "http://127.0.0.1:8000"
        : "https://threadflow-backend.vercel.app";
    const apiBase =
      process.env.BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      defaultBackend;
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase.replace(/\/$/, "")}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
