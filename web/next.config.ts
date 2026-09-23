import type { NextConfig } from "next";

// Fully static: the site is rebuilt from the pipeline's files and needs no server.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  turbopack: { root: __dirname },
};

export default nextConfig;
