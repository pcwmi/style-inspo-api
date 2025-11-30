/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['localhost'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.s3.amazonaws.com',
      },
      {
        protocol: 'https',
        hostname: '*.s3.*.amazonaws.com',
      },
      {
        protocol: 'https',
        hostname: 'style-inspo.s3.us-east-2.amazonaws.com',
      },
      {
        protocol: 'https',
        hostname: '*.cloudfront.net',
      },
    ],
  },
}

module.exports = nextConfig

