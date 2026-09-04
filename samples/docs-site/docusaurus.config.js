// @ts-check

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'AI-LUP Docs',
  tagline: 'PB, PRD, ADR, AC e Histórias — servidos via MCP para a automação',
  url: 'http://localhost:3000',
  baseUrl: '/',
  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',
  organizationName: 'ai-lup',
  projectName: 'docs-site',
  i18n: {
    defaultLocale: 'pt-BR',
    locales: ['pt-BR'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          routeBasePath: '/',
          sidebarPath: require.resolve('./sidebars.js'),
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  // docusaurus-plugin-mcp-server: emite build/mcp/{docs,search-index,manifest}.json
  // no `docusaurus build`, consumidos pelo servidor MCP local (scripts/mcp-server.js).
  plugins: [
    [
      'docusaurus-plugin-mcp-server',
      {
        server: {
          name: 'ai-lup-docs',
        },
      },
    ],
  ],
};

module.exports = config;
