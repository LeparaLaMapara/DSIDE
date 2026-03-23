/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.supabase.co',
      },
      {
        protocol: 'https',
        hostname: 'municipaldata.treasury.gov.za',
      },
      {
        protocol: 'https',
        hostname: 'vulekamali.gov.za',
      },
    ],
  },
};

export default nextConfig;
