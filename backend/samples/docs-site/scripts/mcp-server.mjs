// Local MCP server for this Docusaurus site, per the docusaurus-plugin-mcp-server
// setup guide (https://github.com/scalvert/docusaurus-plugin-mcp-server). Reads the
// artifacts `docusaurus build` emits under build/mcp/ and serves them over HTTP so
// Claude Code (via --mcp-config, ADR-002) can connect with docs_search/docs_fetch.
//
// .mjs (not .js) so it's ESM regardless of this package's own "type" field — the
// plugin package itself is ESM-only.
//
// Usage: node scripts/mcp-server.mjs   (after `npm run build`)

import { createNodeServer } from 'docusaurus-plugin-mcp-server/adapters/node';

const port = Number(process.env.PORT || 3456);

const server = createNodeServer({
  docsPath: './build/mcp/docs.json',
  indexPath: './build/mcp/search-index.json',
  name: 'ai-lup-docs',
});

server.listen(port, () => {
  // No '/mcp' suffix for the plain createNodeServer() case — confirmed against the
  // plugin's own README example: `claude mcp add --transport http my-docs http://localhost:3456`
  console.log(`MCP server running at http://localhost:${port}`);
});
