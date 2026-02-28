import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  typescript: {
    ignoreBuildErrors: true,
  },
  webpack: (config, { isServer, webpack }) => {
    if (!isServer) {
      config.resolve = config.resolve ?? {};
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
      };
    }
    // Ignore cornerstone WASM codec modules that fail to resolve at build time.
    // These are loaded dynamically at runtime via the cornerstone-viewer component.
    config.plugins.push(
      new webpack.IgnorePlugin({
        resourceRegExp:
          /codec-charls|codec-libjpeg-turbo-8bit|codec-openjpeg|codec-openjph/,
      }),
    );
    return config;
  },
  async rewrites() {
    const apiOrigin = process.env.API_ORIGIN ?? "http://localhost:8000";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
