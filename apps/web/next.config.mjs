/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The FastAPI backend is the canonical API. Next.js is a thin UI/BFF layer
  // and must not reimplement banking logic; it only forwards to this base URL.
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1",
  },
};

export default nextConfig;
